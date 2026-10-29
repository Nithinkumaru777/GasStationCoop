-- Gas Station Simulator Co-op Probe & Sync Layer (UE4SS v3.0.1 Lua Mod)
-- Game: Gas Station Simulator (UE 4.27.2)
-- Build: Steam 22000268 / GSS2-Win64-Shipping.exe

-- Fix UE4SS UEHelpers bug (global Print vs print)
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

-- Safely execute operations on Unreal's Game Thread
local function SafeExec(fn)
    ExecuteInGameThread(function()
        local s, err = pcall(fn)
        if not s then
            Log("ERROR: " .. tostring(err))
        end
    end)
end

-- Dump World, GameMode, Controllers, and Pawns
local function DumpWorldState()
    SafeExec(function()
        Log("=== [WORLD & PLAYER STATE DUMP] ===")
        local World = GetCurrentWorld()
        if not World or not World:IsValid() then
            Log("World is currently INVALID")
            return
        end
        Log("World: " .. World:GetFullName())

        local AuthGameMode = World.AuthorityGameMode
        if AuthGameMode and AuthGameMode:IsValid() then
            Log("GameMode: " .. AuthGameMode:GetFullName())
        else
            Log("GameMode: nil (Client role or not authority)")
        end

        local NetDriver = World.NetDriver
        if NetDriver and NetDriver:IsValid() then
            Log("NetDriver: " .. NetDriver:GetFullName())
        else
            Log("NetDriver: None (Standalone mode)")
        end

        local PlayerControllers = FindAllOf("PlayerController")
        if PlayerControllers then
            Log(string.format("PlayerControllers count: %d", #PlayerControllers))
            for i, PC in ipairs(PlayerControllers) do
                if PC:IsValid() then
                    local Pawn = PC.Pawn
                    local PawnName = (Pawn and Pawn:IsValid() and Pawn:GetFullName()) or "None"
                    Log(string.format("  PC[%d]: %s (Pawn: %s)", i, PC:GetFullName(), PawnName))
                end
            end
        end

        local Characters = FindAllOf("Character")
        if Characters then
            Log(string.format("Characters in world: %d", #Characters))
            for i, Char in ipairs(Characters) do
                if Char:IsValid() then
                    local Loc = Char:K2_GetActorLocation()
                    Log(string.format("  Char[%d]: %s @ (X:%.1f, Y:%.1f, Z:%.1f)", i, Char:GetFullName(), Loc.X, Loc.Y, Loc.Z))
                end
            end
        end
        Log("=== [END DUMP] ===")
    end)
end

-- Host Listen Server
local function HostListenServer()
    SafeExec(function()
        Log("Starting listen server...")
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        local World = GetCurrentWorld()
        if Kismet and Kismet:IsValid() and World and World:IsValid() then
            local MapName = World:GetFullName()
            local match = MapName:match("/Game/[%w_/]+")
            if not match then
                match = "/Game/Maps/MenuMap/MainMenu4/Menu_Map4"
            end
            local Cmd = "open " .. match .. "?listen"
            Log("Executing console command: " .. Cmd)
            Kismet:ExecuteConsoleCommand(World, Cmd, nil)
        else
            Log("Failed to locate KismetSystemLibrary or valid World")
        end
    end)
end

-- Join Local Host
local function JoinServer(ip)
    local target = ip or "127.0.0.1:7777"
    SafeExec(function()
        Log("Connecting to server: " .. target)
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        local World = GetCurrentWorld()
        if Kismet and Kismet:IsValid() and World and World:IsValid() then
            local Cmd = "open " .. target
            Log("Executing console command: " .. Cmd)
            Kismet:ExecuteConsoleCommand(World, Cmd, nil)
        else
            Log("Failed to locate KismetSystemLibrary or valid World")
        end
    end)
end

-- ============================================================
-- Dynamic Role Management (Minecraft-Style In-Game Selection)
-- ============================================================
local Role = nil -- nil until player clicks Host or Join in menu

local function LockAndSetRole(wanted)
    if Role == wanted then return true end
    Role = wanted
    Log(string.format("[ROLE] Process role committed to '%s'!", Role))

    -- Persist to role.txt and net/role.txt so background relay detects it immediately
    local f1 = io.open("role.txt", "w")
    if f1 then f1:write(Role .. "\n") f1:close() end

    local f2 = io.open("net/role.txt", "w")
    if f2 then f2:write(Role .. "\n") f2:close() end

    local f3 = io.open("Mods/GasStationCoop/role.txt", "w")
    if f3 then f3:write(Role .. "\n") f3:close() end

    return true
end

-- Automated SDK Dump Runner
local function RunSDKDump()
    SafeExec(function()
        Log("=== [STARTING AUTOMATED SDK GENERATION] ===")
        if GenerateSDK then pcall(GenerateSDK) end
        if DumpAllObjects then pcall(DumpAllObjects) end
        if GenerateUHTCompatibleHeaders then pcall(GenerateUHTCompatibleHeaders) end
        if DumpUSMAP then pcall(DumpUSMAP) end
        Log("=== [SDK GENERATION FINISHED] ===")
    end)
end

-- Check for automated dump trigger
local dumpTriggerFile = "run_dump.txt"
local fDump = io.open(dumpTriggerFile, "r")
if fDump then
    fDump:close()
    os.remove(dumpTriggerFile)
    LoopAsync(3000, function()
        RunSDKDump()
        return true
    end)
end

-- Auto Network & Multi-instance Status Monitor
local function MonitorNetwork()
    LoopAsync(4000, function()
        SafeExec(function()
            local World = GetCurrentWorld()
            if not World or not World:IsValid() then return false end
            local PCs = FindAllOf("PlayerController") or {}
            local NetDriver = World.NetDriver
            local ndName = (NetDriver and NetDriver:IsValid() and NetDriver:GetFullName()) or "None"
            Log(string.format("[STATUS] Role: %s | NetDriver: %s | PlayerControllers: %d", tostring(Role), ndName, #PCs))
        end)
        return false
    end)
end
MonitorNetwork()

-- ============================================================
-- Gas Station Simulator Co-op Puppet & State Sync Engine
-- ============================================================
local PuppetActor = nil
local lastPuppetSpawnAttempt = 0

local function EnsureNetDir()
    os.execute("cmd /c if not exist net mkdir net")
end
EnsureNetDir()

local function GetLocalPlayer()
    local chars = FindAllOf("PlayerCharacter_BP_C") or FindAllOf("GSSPlayerCharacter") or FindAllOf("Character")
    if not chars or #chars == 0 then return nil end
    for _, c in ipairs(chars) do
        if c:IsValid() and c ~= PuppetActor then
            return c
        end
    end
    return nil
end

local function IsInGameplayWorld()
    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return false end
    local name = World:GetFullName():lower()
    if name:find("menu") then return false end
    return GetLocalPlayer() ~= nil
end

local function SyncLocalPlayerState()
    SafeExec(function()
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
    end)
end

local function DriveRemotePuppet()
    SafeExec(function()
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

        -- Adopt or summon puppet if missing (only in gameplay world with 3s cooldown)
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
                        Log("Adopted remote puppet: " .. PuppetActor:GetFullName())

                        local localPlayer = GetLocalPlayer()
                        if localPlayer and localPlayer:IsValid() and localPlayer.Mesh and localPlayer.Mesh:IsValid() then
                            local skMesh = localPlayer.Mesh.SkeletalMesh
                            if skMesh and skMesh:IsValid() and PuppetActor.SkeletalMeshComponent and PuppetActor.SkeletalMeshComponent:IsValid() then
                                pcall(function()
                                    PuppetActor.SkeletalMeshComponent:SetSkeletalMesh(skMesh, true)
                                    local scale = localPlayer.Mesh:K2_GetComponentScale()
                                    if scale then
                                        PuppetActor.SkeletalMeshComponent:SetWorldScale3D(scale)
                                    end
                                    Log("Dressed remote puppet with player mesh: " .. skMesh:GetFullName())
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
    end)
end

-- Client-Side Simulation Suppression
local function ApplyGuestSuppression()
    if Role == "guest" then
        local aiManagers = FindAllOf("GSSAIManager_BP_C") or FindAllOf("AIManager") or {}
        for _, mgr in ipairs(aiManagers) do
            if mgr:IsValid() then
                mgr:SetActorTickEnabled(false)
            end
        end
    end
end

-- ============================================================
-- Phase 6: Subsystem Synchronization Layer
-- ============================================================
local function SendEvent(eventLine)
    local f = io.open("net/events.out", "a")
    if f then
        f:write(eventLine .. "\n")
        f:close()
    end
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
                        Log(string.format("Synced shared wallet from peer: $%.2f (delta: %+.2f)", targetMoney, delta))
                    end
                end
            end

        elseif cmd == "ADD_MONEY" then
            local amount = tonumber(args)
            if amount and Role == "host" and UEHelpers and UEHelpers.GetPlayerController then
                local pc = UEHelpers.GetPlayerController()
                if pc and pc:IsValid() then
                    pcall(function() pc:Cheat_AddMoney(amount) end)
                    Log(string.format("Applied client money delta on host authority: %+.2f", amount))
                end
            end

        elseif cmd == "REGISTER_LOCK" then
            RemoteRegisterLocked = true
            Log("Cash register locked by partner.")

        elseif cmd == "REGISTER_UNLOCK" then
            RemoteRegisterLocked = false
            Log("Cash register unlocked.")

        elseif cmd == "FUEL_DONE" then
            local diff = tonumber(args) or 0.0
            Log(string.format("Remote player finished fueling with diff %.2f", diff))

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
                            local distSq = dx*dx + dy*dy + dz*dz
                            if distSq < (250.0 * 250.0) then
                                Log("Destroying synced trash item: " .. item:GetFullName())
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
                Log("Synced Gas Station Open state: " .. tostring(isOpen))
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
        if cmd then
            HandleCoopEvent(cmd, rest)
        end
    end
end

-- 1 Hz Host Economy & Wallet Monitor
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

-- Game Event Hooks
pcall(function()
    RegisterHook("/Game/Blueprints/Widgets/MiniGames/FuelMiniGame.FuelMiniGame_C:FuelFinished_AchievementEvent", function(self, TargetDifference)
        local diff = 0.0
        pcall(function() diff = TargetDifference:get() end)
        SendEvent(string.format("FUEL_DONE %.2f", diff))
        Log(string.format("Local player finished fueling (TargetDifference: %.2f)", diff))
    end)
end)

pcall(function()
    RegisterHook("/Game/Blueprints/Buildings/Trash/00_TrashItem.00_TrashItem_C:SimpleInteraction", function(self, Pawn, Comp)
        SafeExec(function()
            local item = self:get()
            if item and item:IsValid() then
                local loc = item:K2_GetActorLocation()
                if loc then
                    SendEvent(string.format("TRASH_PICKUP %.1f %.1f %.1f", loc.X, loc.Y, loc.Z))
                    Log(string.format("Local player picked up trash @ (%.1f, %.1f, %.1f)", loc.X, loc.Y, loc.Z))
                end
            end
        end)
    end)
end)

pcall(function()
    RegisterHook("/Script/GSS2.CashShop:OnInteraction", function(self, Instigator)
        if RemoteRegisterLocked then
            Log("WARNING: Cash Register is currently in use by co-op partner!")
        end
    end)
end)

-- 30 Hz Sync Loop
LoopAsync(33, function()
    SyncLocalPlayerState()
    DriveRemotePuppet()
    ProcessIncomingEvents()
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
-- In-Game Co-op Server Browser & Main Menu Integration
-- ============================================================
local DiscoveredServerName = "Scanning for LAN Server..."
local DiscoveredServerIP = ""
local ServerStatus = "OFFLINE"
local RelayLaunched = false

local function ReadServerInfo()
    local f = io.open("net/server_info.txt", "r")
    if not f then return end
    local content = f:read("*all")
    f:close()
    if not content or content == "" then return end

    for line in content:gmatch("[^\r\n]+") do
        local k, v = line:match("^([%w_]+)=(.*)$")
        if k == "SERVER_NAME" then DiscoveredServerName = v end
        if k == "IP" then DiscoveredServerIP = v end
        if k == "STATUS" then ServerStatus = v end
    end
end

-- Launch the relay automatically in background if not already started
local function EnsureBackgroundRelay()
    if RelayLaunched then return end
    RelayLaunched = true
    SafeExec(function()
        os.execute("cmd /c if not exist net mkdir net")
        Log("[IN-GAME] Starting background Co-op LAN Daemon...")
        os.execute('start /b python "gss_relay.py" --mode auto --port 7777 --netdir "net"')
    end)
end

-- Refresh and customize Main Menu
local function UpdateMainMenuUI()
    ReadServerInfo()

    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    for _, menu in ipairs(menus) do
        if menu:IsValid() and menu.DLCButton and menu.DLCButton:IsValid() then
            local btn = menu.DLCButton
            pcall(function()
                if Role == "host" then
                    btn.Text = "CO-OP SERVER (HOSTING)"
                    if btn.ButtonText and btn.ButtonText:IsValid() then
                        btn.ButtonText:SetText("CO-OP SERVER (HOSTING)")
                    end
                elseif Role == "guest" then
                    btn.Text = "CO-OP (CONNECTED)"
                    if btn.ButtonText and btn.ButtonText:IsValid() then
                        btn.ButtonText:SetText("CO-OP (CONNECTED)")
                    end
                else
                    -- Dynamic Minecraft-Style Selection
                    if ServerStatus == "ONLINE" and DiscoveredServerIP ~= "" then
                        btn.Text = "JOIN: " .. DiscoveredServerName:upper()
                        if btn.ButtonText and btn.ButtonText:IsValid() then
                            btn.ButtonText:SetText("JOIN: " .. DiscoveredServerName:upper())
                        end
                    else
                        btn.Text = "HOST CO-OP GAME"
                        if btn.ButtonText and btn.ButtonText:IsValid() then
                            btn.ButtonText:SetText("HOST CO-OP GAME")
                        end
                    end
                end
                btn:SetupButtonText()
            end)
        end
    end

    -- Draw Minecraft-style on-screen banner in Main Menu
    local World = GetCurrentWorld()
    if World and World:IsValid() and World:GetFullName():lower():find("menu") then
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        if Kismet and Kismet:IsValid() then
            local banner = ""
            local color = {R = 0.0, G = 1.0, B = 0.5, A = 1.0}
            if Role == "host" then
                banner = "[CO-OP HOST] Server Active! Friends can detect and join your Gas Station now."
            elseif Role == "guest" then
                banner = string.format("[CO-OP GUEST] Connected to '%s' (%s:7777)! Enjoy Co-op!", DiscoveredServerName, DiscoveredServerIP)
            elseif ServerStatus == "ONLINE" and DiscoveredServerIP ~= "" then
                banner = string.format("✨ [LAN GAME FOUND] '%s' (%s:7777) | Click [JOIN] in menu, or press [F9] to Host!", DiscoveredServerName, DiscoveredServerIP)
            else
                banner = "[CO-OP BROWSER] Scanning LAN for games... Click [HOST CO-OP GAME] to host your station for friends! (F9=Host, F8=Join)"
                color = {R = 1.0, G = 0.85, B = 0.2, A = 1.0}
            end
            pcall(function()
                Kismet:PrintString(World, banner, true, false, color, 1.8)
            end)
        end
    end
end

-- Host Game Action
local function ExecuteHostGame(menu)
    Log("[IN-GAME] Hosting Co-op Server! Loading Gas Station...")
    LockAndSetRole("host")
    HostListenServer()
    if menu and menu:IsValid() then
        if menu.ContinueButton and menu.ContinueButton:IsValid() and menu.bCanBeLoaded then
            menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
        else
            menu:StartNewGame()
        end
    end
end

-- Join Game Action
local function ExecuteJoinGame(menu, ip)
    local target = ip or DiscoveredServerIP or "127.0.0.1:7777"
    Log(string.format("[IN-GAME] Joining server '%s' (%s)...", DiscoveredServerName, target))
    LockAndSetRole("guest")
    JoinServer(target)
    if menu and menu:IsValid() then
        if menu.ContinueButton and menu.ContinueButton:IsValid() and menu.bCanBeLoaded then
            menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
        else
            menu:StartNewGame()
        end
    end
end

-- Hook Main Menu DLC Button Click to trigger Host or Join
pcall(function()
    RegisterHook("/Game/Blueprints/Widgets/MainMenu/MainMenuOverviewWidgetBP.MainMenuOverviewWidgetBP_C:BndEvt__MainMenuOverviewWidgetBP_DLCButton_K2Node_ComponentBoundEvent_3_OnClicked__DelegateSignature", function(self)
        SafeExec(function()
            local menu = self:get()
            ReadServerInfo()

            if Role == "host" or Role == "guest" then
                -- Already committed, continue into station
                if menu.ContinueButton and menu.ContinueButton:IsValid() and menu.bCanBeLoaded then
                    menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
                else
                    menu:StartNewGame()
                end
                return
            end

            -- If an online server is detected, clicking JOIN joins that server!
            if ServerStatus == "ONLINE" and DiscoveredServerIP ~= "" then
                ExecuteJoinGame(menu, DiscoveredServerIP)
            else
                -- Otherwise, clicking HOST starts hosting your station!
                ExecuteHostGame(menu)
            end
        end)
    end)
end)

-- Register Keybinds (F9 = Host, F8 = Join Server)
RegisterKeyBind(Key.F6, function()
    RunSDKDump()
end)

RegisterKeyBind(Key.F7, function()
    DumpWorldState()
end)

RegisterKeyBind(Key.F8, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteJoinGame(menu, DiscoveredServerIP)
end)

RegisterKeyBind(Key.F9, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteHostGame(menu)
end)

-- Auto-start background relay and monitor menu every 1.5s
LoopAsync(1500, function()
    EnsureBackgroundRelay()
    UpdateMainMenuUI()
    return false
end)

Log("GasStationCoop initialized. In-game Co-op Menu & Server Browser active.")
