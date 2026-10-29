-- Gas Station Simulator Co-op Probe & Sync Layer (UE4SS v3.0.1 Lua Mod)
-- Game: Gas Station Simulator (UE 4.27.2)
-- Build: Steam 22000268 / GSS2-Win64-Shipping.exe

if not Print then Print = print end

local ModName = "GasStationCoop"
print(string.format("[%s] Initializing Co-op Mod Probe for Gas Station Simulator...", ModName))

local UEHelpers = nil
local status, res = pcall(require, "UEHelpers")
if status then
    UEHelpers = res
else
    print(string.format("[%s] WARNING: UEHelpers could not be required directly: %s", ModName, tostring(res)))
end

local function Log(msg)
    print(string.format("[%s] %s", ModName, tostring(msg)))
end

local function GetCurrentWorld()
    local worlds = FindAllOf("World")
    if worlds and #worlds > 0 then
        for _, w in ipairs(worlds) do
            if w:IsValid() and not w:GetFullName():find("World /Engine/") then
                return w
            end
        end
    end
    if UEHelpers and UEHelpers.GetWorld then
        local status, w = pcall(UEHelpers.GetWorld)
        if status and w and w:IsValid() then return w end
    end
    return nil
end

local function SafeExec(fn)
    ExecuteInGameThread(function()
        local s, err = pcall(fn)
        if not s then
            Log("ERROR: " .. tostring(err))
        end
    end)
end

local function DumpWorldState()
    SafeExec(function()
        Log("=== [WORLD & PLAYER STATE DUMP] ===")
        local World = GetCurrentWorld()
        if not World or not World:IsValid() then return end
        Log("World: " .. World:GetFullName())

        local AuthGameMode = World.AuthorityGameMode
        Log("GameMode: " .. (AuthGameMode and AuthGameMode:IsValid() and AuthGameMode:GetFullName() or "nil"))

        local NetDriver = World.NetDriver
        Log("NetDriver: " .. (NetDriver and NetDriver:IsValid() and NetDriver:GetFullName() or "None"))

        local PCs = FindAllOf("PlayerController") or {}
        Log(string.format("PlayerControllers count: %d", #PCs))
        Log("=== [END DUMP] ===")
    end)
end

-- Network Relay Activation (Background UDP State Broker)
local function StartHostRelay()
    SafeExec(function()
        Log("[CO-OP] Starting host relay on UDP port 7777...")
        os.execute("cmd /c if not exist net mkdir net")
        os.execute('start "" pythonw "gss_relay.py" --mode host --port 7777 --netdir "net"')
    end)
end

local function StartGuestRelay(targetIP)
    SafeExec(function()
        local ip = targetIP or "127.0.0.1"
        Log(string.format("[CO-OP] Starting client relay connecting to %s:7777...", ip))
        os.execute("cmd /c if not exist net mkdir net")
        os.execute(string.format('start "" pythonw "gss_relay.py" --mode client --connect %s --port 7777 --netdir "net"', ip))
    end)
end

-- Role Management
local Role = nil

local function ReadSavedRole()
    local f = io.open("role.txt", "r") or io.open("net/role.txt", "r") or io.open("Mods/GasStationCoop/role.txt", "r")
    if f then
        local c = f:read("*all")
        f:close()
        if c then
            local r = c:match("(%a+)")
            if r and (r == "host" or r == "guest") then
                Role = r
                Log(string.format("[ROLE] Pre-selected role loaded: '%s'", Role))
                return Role
            end
        end
    end
    return nil
end
ReadSavedRole()

local function LockAndSetRole(wanted)
    if Role == wanted then return true end
    Role = wanted
    Log(string.format("[ROLE] Role locked to '%s'", Role))

    local f1 = io.open("role.txt", "w")
    if f1 then f1:write(Role .. "\n") f1:close() end

    local f2 = io.open("net/role.txt", "w")
    if f2 then f2:write(Role .. "\n") f2:close() end

    local f3 = io.open("Mods/GasStationCoop/role.txt", "w")
    if f3 then f3:write(Role .. "\n") f3:close() end

    return true
end

-- SDK Dump
local function RunSDKDump()
    SafeExec(function()
        if GenerateSDK then pcall(GenerateSDK) end
        if DumpAllObjects then pcall(DumpAllObjects) end
        if GenerateUHTCompatibleHeaders then pcall(GenerateUHTCompatibleHeaders) end
        if DumpUSMAP then pcall(DumpUSMAP) end
    end)
end

-- Puppet & State Sync
local PuppetActor = nil
local lastPuppetSpawnAttempt = 0

local function EnsureNetDir()
    os.execute("cmd /c if not exist net mkdir net")
end
EnsureNetDir()

local CachedLocalPlayer = nil
local function GetLocalPlayer()
    if CachedLocalPlayer and CachedLocalPlayer:IsValid() then
        return CachedLocalPlayer
    end
    CachedLocalPlayer = FindFirstOf("PlayerCharacter_BP_C") or FindFirstOf("GSSPlayerCharacter")
    return CachedLocalPlayer
end

local function IsInGameplayWorld()
    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return false end
    local name = World:GetFullName():lower()
    return name:find("demomapka") ~= nil and GetLocalPlayer() ~= nil
end

local function SyncLocalPlayerState()
    local player = GetLocalPlayer()
    if not player or not player:IsValid() then return end

    local loc = player:K2_GetActorLocation()
    local rot = player:K2_GetActorRotation()
    if not loc or not rot then return end

    local stateStr = string.format("%.2f %.2f %.2f %.2f %.2f %.2f", loc.X, loc.Y, loc.Z, rot.Pitch, rot.Yaw, rot.Roll)
    local f = io.open("net/local_player.state", "w")
    if f then
        f:write(stateStr)
        f:close()
    end
end

local function DriveRemotePuppet()
    local f = io.open("net/remote_player.state", "r")
    if not f then return end
    local line = f:read("*line")
    f:close()
    if not line or line == "" then return end

    local x, y, z, pitch, yaw, roll = line:match("([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)")
    if not x then return end

    x, y, z = tonumber(x), tonumber(y), tonumber(z)
    pitch, yaw, roll = tonumber(pitch), tonumber(yaw), tonumber(roll)

    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return end

    if not PuppetActor or not PuppetActor:IsValid() then
        local now = os.time()
        if IsInGameplayWorld() and (now - lastPuppetSpawnAttempt >= 3) then
            lastPuppetSpawnAttempt = now
            local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
            if Kismet and Kismet:IsValid() then
                Kismet:ExecuteConsoleCommand(World, "summon SkeletalMeshActor", nil)
                local newActors = FindAllOf("SkeletalMeshActor") or {}
                if #newActors > 0 then
                    PuppetActor = newActors[#newActors]
                    local localPlayer = GetLocalPlayer()
                    if localPlayer and localPlayer:IsValid() and localPlayer.Mesh and localPlayer.Mesh:IsValid() then
                        local skMesh = localPlayer.Mesh.SkeletalMesh
                        if skMesh and skMesh:IsValid() and PuppetActor.SkeletalMeshComponent and PuppetActor.SkeletalMeshComponent:IsValid() then
                            pcall(function()
                                PuppetActor.SkeletalMeshComponent:SetSkeletalMesh(skMesh, true)
                                local scale = localPlayer.Mesh:K2_GetComponentScale()
                                if scale then PuppetActor.SkeletalMeshComponent:SetWorldScale3D(scale) end
                                pcall(function() PuppetActor:SetActorEnableCollision(false) end)
                                pcall(function() PuppetActor.SkeletalMeshComponent:SetCollisionEnabled(0) end)
                            end)
                        end
                    end
                end
            end
        end
    end

    if PuppetActor and PuppetActor:IsValid() then
        local newLoc = {X = x, Y = y, Z = z}
        local newRot = {Pitch = pitch, Yaw = yaw, Roll = roll}
        PuppetActor:K2_SetActorLocationAndRotation(newLoc, newRot, false, nil, false)
    end
end

local function ApplyGuestSuppression()
    if Role == "guest" then
        local aiManagers = FindAllOf("GSSAIManager_BP_C") or FindAllOf("AIManager") or {}
        for _, mgr in ipairs(aiManagers) do
            if mgr:IsValid() then mgr:SetActorTickEnabled(false) end
        end
    end
end

-- Event Sync Layer
local function SendEvent(eventLine)
    local f = io.open("net/events.out", "a")
    if f then f:write(eventLine .. "\n") f:close() end
end

local RemoteRegisterLocked = false
local LastSyncedMoney = nil

local function HandleCoopEvent(cmd, args)
    SafeExec(function()
        if cmd == "MONEY" then
            local targetMoney = tonumber(args)
            if targetMoney and UEHelpers and UEHelpers.GetPlayerController then
                local pc = UEHelpers.GetPlayerController()
                if pc and pc:IsValid() then
                    local cur = pc:GetMoney()
                    local delta = targetMoney - cur
                    if math.abs(delta) >= 0.05 then
                        pcall(function() pc:Cheat_AddMoney(delta) end)
                    end
                end
            end

        elseif cmd == "ADD_MONEY" then
            local amount = tonumber(args)
            if amount and Role == "host" and UEHelpers and UEHelpers.GetPlayerController then
                local pc = UEHelpers.GetPlayerController()
                if pc and pc:IsValid() then
                    pcall(function() pc:Cheat_AddMoney(amount) end)
                end
            end

        elseif cmd == "REGISTER_LOCK" then
            RemoteRegisterLocked = true

        elseif cmd == "REGISTER_UNLOCK" then
            RemoteRegisterLocked = false

        elseif cmd == "FUEL_DONE" then
            Log(string.format("Partner completed fueling: %s", tostring(args)))

        elseif cmd == "TRASH_PICKUP" then
            local x, y, z = args:match("([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)")
            if x and y and z then
                x, y, z = tonumber(x), tonumber(y), tonumber(z)
                local trashItems = FindAllOf("00_TrashItem_C") or FindAllOf("TrashItemBase") or {}
                for _, item in ipairs(trashItems) do
                    if item:IsValid() then
                        local loc = item:K2_GetActorLocation()
                        if loc then
                            local dx = loc.X - x
                            local dy = loc.Y - y
                            local dz = loc.Z - z
                            if (dx*dx + dy*dy + dz*dz) < (250.0 * 250.0) then
                                pcall(function() item:K2_DestroyActor() end)
                                break
                            end
                        end
                    end
                end
            end

        elseif cmd == "STATION_OPEN" then
            local isOpen = (tonumber(args) == 1)
            local worlds = FindAllOf("GSSGameState_BP_C") or FindAllOf("GSSGameState") or {}
            if #worlds > 0 and worlds[1]:IsValid() then
                pcall(function() worlds[1]:CloseOpenGasStation(isOpen) end)
            end
        end
    end)
end

local function ProcessIncomingEvents()
    local f = io.open("net/events.in", "r")
    if not f then return end
    local content = f:read("*all")
    f:close()
    if not content or content == "" then return end

    f = io.open("net/events.in", "w")
    if f then f:close() end

    for line in content:gmatch("[^\r\n]+") do
        local cmd, rest = line:match("^(%S+)%s*(.*)$")
        if cmd then HandleCoopEvent(cmd, rest) end
    end
end

-- 1 Hz Host Economy Sync
local function SyncEconomyLoop()
    if Role == "host" and UEHelpers and UEHelpers.GetPlayerController then
        SafeExec(function()
            local pc = UEHelpers.GetPlayerController()
            if pc and pc:IsValid() then
                local money = nil
                pcall(function() money = pc:GetMoney() end)
                if money then
                    if LastSyncedMoney == nil or math.abs(money - LastSyncedMoney) >= 0.05 then
                        LastSyncedMoney = money
                        SendEvent(string.format("MONEY %.2f", money))
                    end
                end
            end
        end)
    end
end

-- Game Hooks
pcall(function()
    RegisterHook("/Game/Blueprints/Widgets/MiniGames/FuelMiniGame.FuelMiniGame_C:FuelFinished_AchievementEvent", function(self, TargetDifference)
        local diff = 0.0
        pcall(function() diff = TargetDifference:get() end)
        SendEvent(string.format("FUEL_DONE %.2f", diff))
    end)
end)

pcall(function()
    RegisterHook("/Game/Blueprints/Buildings/Trash/00_TrashItem.00_TrashItem_C:SimpleInteraction", function(self, Pawn, Comp)
        SafeExec(function()
            local item = self:get()
            if item and item:IsValid() then
                local loc = item:K2_GetActorLocation()
                if loc then SendEvent(string.format("TRASH_PICKUP %.1f %.1f %.1f", loc.X, loc.Y, loc.Z)) end
            end
        end)
    end)
end)

pcall(function()
    RegisterHook("/Script/GSS2.CashShop:OnInteraction", function(self, Instigator)
        if RemoteRegisterLocked then Log("WARNING: Cash register locked by partner!") end
    end)
end)

-- Loops
LoopAsync(50, function()
    SafeExec(function()
        SyncLocalPlayerState()
        DriveRemotePuppet()
        ProcessIncomingEvents()
    end)
    return false
end)

LoopAsync(1000, function()
    SyncEconomyLoop()
    return false
end)

LoopAsync(3000, function()
    ApplyGuestSuppression()
    return false
end)

-- ============================================================
-- Silent Background Relay & Safe On-Screen Co-op UI
-- ============================================================
local RelayLaunched = false

local function EnsureBackgroundRelay()
    if RelayLaunched then return end
    RelayLaunched = true
    SafeExec(function()
        os.execute("cmd /c if not exist net mkdir net")
        -- Use pythonw.exe so ZERO command windows appear on the user's desktop!
        os.execute('start "" pythonw "gss_relay.py" --mode auto --port 7777 --netdir "net"')
    end)
end

-- Safe Main Menu Display (NEVER modifies FText directly to prevent crashes)
local function UpdateMainMenuUI()
    local World = GetCurrentWorld()
    if World and World:IsValid() and World:GetFullName():lower():find("menu") then
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        if Kismet and Kismet:IsValid() then
            local banner = ""
            local color = {R = 0.0, G = 1.0, B = 0.5, A = 1.0}
            if Role == "host" then
                banner = "[CO-OP HOST ACTIVE] Server live on port 7777! Share your IP with friends."
            elseif Role == "guest" then
                banner = "[CO-OP CONNECTED] Synced with Host! Co-op Station ready."
            else
                banner = "GAS STATION CO-OP:  [F9] HOST A WORLD   |   [F8] JOIN A WORLD   |   (or click DLC on menu)"
                color = {R = 1.0, G = 0.85, B = 0.2, A = 1.0}
            end
            pcall(function()
                Kismet:PrintString(World, banner, true, false, color, 1.8)
            end)
        end
    end
end

-- ============================================================
-- Robust Multi-Stage Station Level Entry Layer
-- ============================================================
local HasEnteredGameplay = false
local LevelAttemptCount = 0
local LastAttemptTime = 0

local function TryTriggerLevelLoad(menu)
    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return false end
    local wname = World:GetFullName():lower()

    if wname:find("demomapka") and GetLocalPlayer() ~= nil then
        if not HasEnteredGameplay then
            HasEnteredGameplay = true
            Log("[CO-OP] *** SUCCESSFULLY INSIDE STATION GAMEPLAY (DemoMapka)! ***")
        end
        return true
    end

    if not menu or not menu:IsValid() then
        local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
        if #menus > 0 and menus[1]:IsValid() then
            menu = menus[1]
        end
    end

    LevelAttemptCount = LevelAttemptCount + 1
    Log(string.format("[CO-OP] Station Level Load Attempt #%d (Role: %s)...", LevelAttemptCount, tostring(Role)))

    if menu and menu:IsValid() then
        -- Stage 1: Try Continue Button (loads starter save into station)
        local canLoad = false
        pcall(function() canLoad = menu.bCanBeLoaded end)

        if canLoad then
            Log("[CO-OP] [STAGE 1] Save slot confirmed (bCanBeLoaded=true)! Clicking Continue Button...")
            local s, err = pcall(function()
                menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
            end)
            if s then
                Log("[CO-OP] ContinueButton executed successfully!")
                return true
            else
                Log("[CO-OP] ContinueButton failed: " .. tostring(err))
            end
        else
            Log("[CO-OP] Save slot reading in progress (bCanBeLoaded=false)...")
        end

        -- Stage 2: If MapSelectionWidget is active, click first map (Route 66 / Desert Station)
        pcall(function()
            if menu.MapSelectionWidget and menu.MapSelectionWidget:IsValid() then
                Log("[CO-OP] [STAGE 2] MapSelectionWidget active! Clicking first map button...")
                local buttons = menu.MapSelectionWidget.MapsButtons
                if buttons and #buttons > 0 and buttons[1]:IsValid() then
                    pcall(function() buttons[1]:GamePadClick() end)
                    pcall(function() buttons[1]:BndEvt__WBP_MapSelectionButton_Button_22_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature() end)
                end
            end
        end)

        -- Stage 3: After waiting 5 attempts (~6-8s), try NewGameButton if still not loaded
        if LevelAttemptCount >= 5 and not canLoad then
            Log("[CO-OP] [STAGE 3] Triggering NewGameButton...")
            pcall(function()
                menu:BndEvt__NewGameButton_K2Node_ComponentBoundEvent_2_OnClicked__DelegateSignature()
                menu:StartNewGame()
            end)
        end
    else
        Log("[CO-OP] MainMenuOverviewWidgetBP not found yet.")
    end

    -- Stage 4: Crash-Proof Console Fallback after 6 attempts
    if LevelAttemptCount >= 6 and World and World:IsValid() then
        Log("[CO-OP] [STAGE 4] Executing crash-proof console fallback: open DemoMapka...")
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        if Kismet and Kismet:IsValid() then
            pcall(function()
                Kismet:ExecuteConsoleCommand(World, "open DemoMapka", nil)
            end)
        end
    end

    return false
end

-- Option 1: Host a World Action
local function ExecuteHostGame(menu)
    Log("[CO-OP] >>> OPTION 1: HOST A WORLD <<<")
    LockAndSetRole("host")
    StartHostRelay()
    TryTriggerLevelLoad(menu)
end

-- Option 2: Join a World Action
local function ExecuteJoinGame(menu, promptForIP)
    Log("[CO-OP] >>> OPTION 2: JOIN A WORLD <<<")
    local targetIP = "127.0.0.1"

    if promptForIP then
        os.execute('start /wait pythonw "coop_menu.py"')
    end

    local f = io.open("host_ip.txt", "r") or io.open("net/host_ip.txt", "r")
    if f then
        local content = f:read("*all")
        f:close()
        if content and content:match("%d+%.%d+%.%d+%.%d+") then
            targetIP = content:match("%d+%.%d+%.%d+%.%d+")
        end
    end

    Log(string.format("[CO-OP] Connecting to Host at %s:7777...", targetIP))
    LockAndSetRole("guest")
    StartGuestRelay(targetIP)
    TryTriggerLevelLoad(menu)
end

-- Hook Main Menu DLC Button Click to open the 2-Option Selector Dialog (SILENT GUI)
pcall(function()
    RegisterHook("/Game/Blueprints/Widgets/MainMenu/MainMenuOverviewWidgetBP.MainMenuOverviewWidgetBP_C:BndEvt__MainMenuOverviewWidgetBP_DLCButton_K2Node_ComponentBoundEvent_3_OnClicked__DelegateSignature", function(self)
        SafeExec(function()
            local menu = self:get()

            if Role == "host" or Role == "guest" then
                if menu.ContinueButton and menu.ContinueButton:IsValid() and menu.bCanBeLoaded then
                    menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
                else
                    menu:StartNewGame()
                end
                return
            end

            Log("[CO-OP] DLC clicked! Opening Host / Join Selector Dialog...")
            -- Use pythonw so zero black cmd windows appear
            os.execute('start /wait pythonw "coop_menu.py"')

            local chosenRole = nil
            local f = io.open("role.txt", "r") or io.open("net/role.txt", "r")
            if f then
                local c = f:read("*all")
                f:close()
                if c then chosenRole = c:match("(%a+)") end
            end

            if chosenRole == "host" then
                ExecuteHostGame(menu)
            elseif chosenRole == "guest" then
                ExecuteJoinGame(menu, false)
            end
        end)
    end)
end)

-- ============================================================
-- Pause Menu & ESC Co-op Fix (Direct, Crash-Proof & Instant)
-- Fixes UE4 multiplayer glitch where Resume button stays stuck
-- on screen or ESC minimizes/loses focus.
-- ============================================================
local function RestoreGameplayInput()
    local pc = (UEHelpers and UEHelpers.GetPlayerController) and UEHelpers.GetPlayerController() or FindFirstOf("PlayerController")
    if pc and pc:IsValid() then
        pcall(function()
            pc.bShowMouseCursor = false
            pc.bEnableClickEvents = false
            pc.bEnableMouseOverEvents = false
            pc:SetIgnoreLookInput(false)
            pc:SetIgnoreMoveInput(false)
        end)
        local WBP = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
        if WBP and WBP:IsValid() then
            pcall(function()
                WBP:SetInputMode_GameOnly(pc)
                WBP:SetFocusToGameViewport()
            end)
        end
    end
end

-- Hook IngameMenuContainer:ResumeGame
pcall(function()
    RegisterHook("/MenuSystemPro/Blueprints/UI/Menus/Ingame/IngameMenuContainerWidgetBP.IngameMenuContainerWidgetBP_C:ResumeGame", function(self)
        local container = self:get()
        if container and container:IsValid() then
            pcall(function() container:RemoveFromViewport() end)
            pcall(function() container:SetVisibility(2) end)
        end
        RestoreGameplayInput()
    end)
end)

-- Hook IngameMenuOverview Resume Button Click
pcall(function()
    RegisterHook("/MenuSystemPro/Blueprints/UI/Menus/Ingame/IngameMenuOverviewWidgetBP.IngameMenuOverviewWidgetBP_C:BndEvt__ResumeButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature", function(self)
        local overview = self:get()
        if overview and overview:IsValid() then
            if overview.IngameMenuWidget and overview.IngameMenuWidget:IsValid() then
                pcall(function() overview.IngameMenuWidget:RemoveFromViewport() end)
                pcall(function() overview.IngameMenuWidget:SetVisibility(2) end)
            end
            pcall(function() overview:RemoveFromViewport() end)
            pcall(function() overview:SetVisibility(2) end)
        end
        RestoreGameplayInput()
    end)
end)

-- Hook IngameMenuOverview:ResumeManualCall
pcall(function()
    RegisterHook("/MenuSystemPro/Blueprints/UI/Menus/Ingame/IngameMenuOverviewWidgetBP.IngameMenuOverviewWidgetBP_C:ResumeManualCall", function(self)
        local overview = self:get()
        if overview and overview:IsValid() then
            if overview.IngameMenuWidget and overview.IngameMenuWidget:IsValid() then
                pcall(function() overview.IngameMenuWidget:RemoveFromViewport() end)
                pcall(function() overview.IngameMenuWidget:SetVisibility(2) end)
            end
            pcall(function() overview:RemoveFromViewport() end)
            pcall(function() overview:SetVisibility(2) end)
        end
        RestoreGameplayInput()
    end)
end)

-- Hook IngameMenuOverview:OnPressedBack (ESC key inside menu)
pcall(function()
    RegisterHook("/MenuSystemPro/Blueprints/UI/Menus/Ingame/IngameMenuOverviewWidgetBP.IngameMenuOverviewWidgetBP_C:OnPressedBack", function(self)
        local overview = self:get()
        if overview and overview:IsValid() then
            if overview.IngameMenuWidget and overview.IngameMenuWidget:IsValid() then
                pcall(function() overview.IngameMenuWidget:RemoveFromViewport() end)
                pcall(function() overview.IngameMenuWidget:SetVisibility(2) end)
            end
            pcall(function() overview:RemoveFromViewport() end)
            pcall(function() overview:SetVisibility(2) end)
        end
        RestoreGameplayInput()
    end)
end)

-- Dedicated Hotkeys:
-- F9 = OPTION 1: HOST A WORLD
RegisterKeyBind(Key.F9, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteHostGame(menu)
end)

-- F8 = OPTION 2: JOIN A WORLD (Pops up IP prompt to join from any Wi-Fi)
RegisterKeyBind(Key.F8, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteJoinGame(menu, true)
end)

RegisterKeyBind(Key.F6, function() RunSDKDump() end)
RegisterKeyBind(Key.F7, function() DumpWorldState() end)

-- Menu update & continuous level enter loop (runs every 1000ms)
LoopAsync(1000, function()
    EnsureBackgroundRelay()
    UpdateMainMenuUI()

    -- Check if we are already in gameplay
    local World = GetCurrentWorld()
    if World and World:IsValid() then
        local wname = World:GetFullName():lower()
        if wname:find("demomapka") and GetLocalPlayer() ~= nil then
            if not HasEnteredGameplay then
                HasEnteredGameplay = true
                Log("[CO-OP] *** CONNECTED TO GAS STATION WORLD! MULTIPLAYER SYNC RUNNING. ***")
            end
            return false
        end
    end

    -- If still in menu and role is host or guest, attempt level entry
    if (Role == "host" or Role == "guest") and not HasEnteredGameplay then
        local now = os.time()
        if now - LastAttemptTime >= 1 then
            LastAttemptTime = now
            ExecuteInGameThread(function()
                local s, err = pcall(TryTriggerLevelLoad, nil)
                if not s then
                    Log("[CO-OP ERROR in TryTriggerLevelLoad] " .. tostring(err))
                end
            end)
        end
    end

    return false
end)

Log("GasStationCoop initialized. In-game 2-Option Co-op Menu active (Host a World / Join a World).")
