-- Gas Station Simulator Co-op Engine & Synchronization Layer
-- Game: Gas Station Simulator (UE 4.27.2)
-- Build: Steam 22000268 / GSS2-Win64-Shipping.exe
-- Lead Architect & Creator: Nithin Kumar (@Nithinkumaru777)
-- GitHub: https://github.com/Nithinkumaru777/GasStationCoop

if not Print then Print = print end

local ModName = "GasStationCoop"
print(string.format("[%s] Initializing Co-op Engine v2.0 for Gas Station Simulator...", ModName))

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

local function SafeExec(fn)
    ExecuteInGameThread(function()
        local s, err = pcall(fn)
        if not s then
            Log("ERROR: " .. tostring(err))
        end
    end)
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
        local s, w = pcall(UEHelpers.GetWorld)
        if s and w and w:IsValid() then return w end
    end
    return nil
end

local function EnsureNetDir()
    os.execute("cmd /c if not exist net mkdir net")
end
EnsureNetDir()

-- ============================================================
-- Profile & Role Management
-- ============================================================
local Role = nil
local LocalName = "Nithin"
local LocalChar = "biker"

local function ReadLocalProfile()
    local f_role = io.open("net/role.txt", "r") or io.open("role.txt", "r") or io.open("Mods/GasStationCoop/role.txt", "r")
    if f_role then
        local c = f_role:read("*all")
        f_role:close()
        if c then
            local r = c:match("(%a+)")
            if r and (r == "host" or r == "guest") then
                Role = r
            end
        end
    end

    local f_name = io.open("net/player_name.txt", "r") or io.open("player_name.txt", "r")
    if f_name then
        local c = f_name:read("*line")
        f_name:close()
        if c and c:match("%S+") then LocalName = c:match("^%s*(.-)%s*$") end
    end

    local f_char = io.open("net/character.txt", "r") or io.open("character.txt", "r")
    if f_char then
        local c = f_char:read("*line")
        f_char:close()
        if c and c:match("%a+") then LocalChar = c:match("(%a+)") end
    end
end
ReadLocalProfile()

local function LockAndSetRole(wanted)
    if Role == wanted then return true end
    Role = wanted
    Log(string.format("[ROLE] Role locked to '%s'", Role))

    local paths = {"net/role.txt", "role.txt", "Mods/GasStationCoop/role.txt"}
    for _, p in ipairs(paths) do
        local f = io.open(p, "w")
        if f then
            f:write(Role .. "\n")
            f:close()
        end
    end
    return true
end

-- ============================================================
-- Network Relay Activation (Background UDP State Broker)
-- ============================================================
local function StartHostRelay()
    Log("[CO-OP] Starting host relay on UDP port 7777...")
    EnsureNetDir()
    os.execute('start "" pythonw "gss_relay.py" --mode host --port 7777 --netdir "net"')
end

local function StartGuestRelay(targetIP)
    local ip = targetIP or "127.0.0.1"
    Log(string.format("[CO-OP] Starting client relay connecting to %s:7777...", ip))
    EnsureNetDir()
    local f = io.open("net/host_ip.txt", "w")
    if f then f:write(ip .. "\n") f:close() end
    os.execute(string.format('start "" pythonw "gss_relay.py" --mode client --connect %s --port 7777 --netdir "net"', ip))
end

local RelayLaunched = false
local function EnsureBackgroundRelay()
    if RelayLaunched then return end
    RelayLaunched = true
    EnsureNetDir()
    os.execute('start "" pythonw "gss_relay.py" --mode auto --port 7777 --netdir "net"')
end

-- ============================================================
-- Peer State & Live Handshake Inspection
-- ============================================================
local IsPeerConnected = false
local RemotePlayerName = "Partner"
local RemotePlayerRole = "GUEST"
local RemotePlayerChar = "delivery"
local LastPeerCheckTime = 0

local function CheckPeerStatus()
    local now = os.time()
    if now - LastPeerCheckTime < 1 then return IsPeerConnected end
    LastPeerCheckTime = now

    local f = io.open("net/peer.state", "r")
    if not f then
        IsPeerConnected = false
        return false
    end

    local content = f:read("*all")
    f:close()
    if not content or content == "" then
        IsPeerConnected = false
        return false
    end

    local connected = content:match("CONNECTED=(%d)")
    local role = content:match("ROLE=(%a+)")
    local name = content:match("NAME=([^\r\n]+)")
    local char_id = content:match("CHAR=(%a+)")

    if connected == "1" then
        IsPeerConnected = true
        if role then RemotePlayerRole = role:upper() end
        if name and name ~= "" then RemotePlayerName = name end
        if char_id and char_id ~= "" then RemotePlayerChar = char_id end
    else
        IsPeerConnected = false
    end

    return IsPeerConnected
end

-- ============================================================
-- World & Player Helpers
-- ============================================================
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

-- ============================================================
-- Character Archetype Assets & Mesh Paths
-- ============================================================
local CharacterMeshes = {
    biker = {
        name = "Route 66 Biker",
        body = "/Game/Assets/Characters/Biker/biker_body_SK.biker_body_SK",
        head = "/Game/Assets/Characters/Biker/Biker_head_SK.Biker_head_SK",
        bp = "/Game/Assets/Characters/Blueprints/Biker/Biker_ActorBp.Biker_ActorBp_C"
    },
    delivery = {
        name = "Fuel Delivery Specialist",
        body = "/Game/Assets/Characters/NewBaseMesh/DeliveryGuys/SK_Ma_GasolineDelivery_T.SK_Ma_GasolineDelivery_T"
    },
    worker = {
        name = "Station Worker",
        body = "/Game/Assets/Characters/PlayerModularSkeleton/Player_Modular_Base_01.Player_Modular_Base_01"
    },
    party = {
        name = "Route 66 Party Guy",
        body = "/Game/Assets/Characters/NewBaseMesh/Party/SK_Ma_BusParty_10.SK_Ma_BusParty_10"
    }
}

local AnimPaths = {
    walk = "/Game/Assets/Characters/Animations/NPCs/Movement/Cleaning/IPC/BaseNPC_Walk_F_IP_02.BaseNPC_Walk_F_IP_02",
    idle = "/Game/Assets/Characters/Animations/NPCs/Movement/Cleaning/IPC/BaseNPC_Standing_Idle_00.BaseNPC_Standing_Idle_00"
}

-- Height of the floating name tag above the puppet's feet (tuning knob).
local NAMETAG_HEIGHT = 200.0

-- StaticFindObject only sees assets already in memory; LoadAsset pulls them from the pak.
local function FindOrLoad(path)
    local o = StaticFindObject(path)
    if (not o or not o:IsValid()) and LoadAsset then
        pcall(function() o = LoadAsset(path) end)
    end
    if o and o:IsValid() then return o end
    Log("[CO-OP] Asset not found: " .. path)
    return nil
end

-- ============================================================
-- Crash-Proof Actor Spawner (No Cheat Commands)
-- ============================================================
local function SpawnActorFromClass(World, ActorClass, loc, rot)
    if not World or not World:IsValid() or not ActorClass or not ActorClass:IsValid() then
        return nil
    end

    local spawned = nil

    -- 1. Try native UE4SS World:SpawnActor
    pcall(function()
        if World.SpawnActor then
            spawned = World:SpawnActor(ActorClass, loc, rot)
        end
    end)
    if spawned and spawned:IsValid() then return spawned end

    -- 2. Try GameplayStatics BeginSpawningActorFromClass
    pcall(function()
        local GPStatics = StaticFindObject("/Script/Engine.Default__GameplayStatics")
        if GPStatics and GPStatics:IsValid() then
            local transform = {
                Rotation = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 },
                Translation = { X = loc.X, Y = loc.Y, Z = loc.Z },
                Scale3D = { X = 1.0, Y = 1.0, Z = 1.0 }
            }
            local actor = GPStatics:BeginSpawningActorFromClass(World, ActorClass, transform, false, nil)
            if actor and actor:IsValid() then
                spawned = GPStatics:FinishSpawningActor(actor, transform)
            end
        end
    end)

    return spawned
end

-- ============================================================
-- 3D Character Puppet & Floating Name Tag Layer
-- ============================================================
local PuppetActor = nil
local NameTagActor = nil
local CachedWalkAnim = nil
local CachedIdleAnim = nil
local IsPuppetWalking = false
local LastPuppetX = 0
local LastPuppetY = 0
local LastSpawnAttempt = 0
-- Height of the mesh pivot (feet) above the actor root; Biker_ActorBp's Body is offset inside the BP
local PuppetMeshOffsetZ = 0.0

local function SpawnRemotePuppet(World, loc, rot)
    if not World or not World:IsValid() then return nil end

    CheckPeerStatus()
    local charKey = RemotePlayerChar or "biker"
    local charDef = CharacterMeshes[charKey] or CharacterMeshes["biker"]
    Log(string.format("[CO-OP] Spawning remote puppet for %s [Archetype: %s]...", RemotePlayerName, charDef.name))

    -- 1. Try spawning Biker BP if archetype is biker
    local newPuppet = nil
    if charKey == "biker" and charDef.bp then
        local bpClass = StaticFindObject(charDef.bp)
        if bpClass and bpClass:IsValid() then
            newPuppet = SpawnActorFromClass(World, bpClass, loc, rot)
        end
    end

    -- 2. General fallback: Spawn SkeletalMeshActor with explicit full-body mesh
    if not newPuppet or not newPuppet:IsValid() then
        local skClass = StaticFindObject("/Script/Engine.SkeletalMeshActor")
        if skClass and skClass:IsValid() then
            newPuppet = SpawnActorFromClass(World, skClass, loc, rot)
        end
    end

    if not newPuppet or not newPuppet:IsValid() then
        Log("[CO-OP ERROR] Could not spawn PuppetActor!")
        return nil
    end

    -- 3. Configure meshes and materials
    pcall(function()
        newPuppet:SetActorEnableCollision(false)
        local skComp = newPuppet.SkeletalMeshComponent or newPuppet.Body
        if skComp and skComp:IsValid() then
            skComp:SetCollisionEnabled(0)
            local bodyMesh = FindOrLoad(charDef.body)
            if bodyMesh then
                skComp:SetSkeletalMesh(bodyMesh, true)
            end
            skComp:SetWorldScale3D({X = 1.0, Y = 1.0, Z = 1.0})

            -- Biker's head is a separate skeletal mesh: make it follow the body's pose
            local head = newPuppet.Head
            if head and head:IsValid() then
                pcall(function() head:SetMasterPoseComponent(skComp, true) end)
            end

            -- Pre-cache animations (PlayAnimation switches the component to SingleNode mode itself)
            CachedWalkAnim = FindOrLoad(AnimPaths.walk)
            CachedIdleAnim = FindOrLoad(AnimPaths.idle)
            if CachedIdleAnim then
                pcall(function()
                    local animSkel = CachedIdleAnim.Skeleton
                    local meshSkel = skComp.SkeletalMesh.Skeleton
                    if animSkel and meshSkel and animSkel:GetFullName() ~= meshSkel:GetFullName() then
                        Log(string.format("[CO-OP] WARNING: anim skeleton %s != mesh skeleton %s (will T-pose)", animSkel:GetFullName(), meshSkel:GetFullName()))
                    end
                end)
                pcall(function() skComp:PlayAnimation(CachedIdleAnim, true) end)
            end
        end
    end)

    PuppetMeshOffsetZ = 0.0
    pcall(function()
        local skComp = newPuppet.SkeletalMeshComponent or newPuppet.Body
        PuppetMeshOffsetZ = skComp:K2_GetComponentLocation().Z - newPuppet:K2_GetActorLocation().Z
    end)

    PuppetActor = newPuppet
    Log(string.format("[CO-OP] Remote puppet successfully spawned: %s (mesh Z offset %.1f)", PuppetActor:GetFullName(), PuppetMeshOffsetZ))

    -- 4. Spawn 3D World Name Tag above Puppet's head
    local tagClass = StaticFindObject("/Script/Engine.TextRenderActor")
    if tagClass and tagClass:IsValid() then
        local tagLoc = { X = loc.X, Y = loc.Y, Z = loc.Z + NAMETAG_HEIGHT }
        NameTagActor = SpawnActorFromClass(World, tagClass, tagLoc, rot)
        if NameTagActor and NameTagActor:IsValid() then
            pcall(function()
                NameTagActor:SetActorEnableCollision(false)
                local tr = NameTagActor.TextRender
                if tr and tr:IsValid() then
                    local label = string.format("⭐ %s [%s]", RemotePlayerName, RemotePlayerRole)
                    tr:SetText(label)
                    tr:SetWorldSize(28.0)
                    tr:SetHorizontalAlignment(1) -- Center
                    tr:SetVerticalAlignment(1)   -- Center
                    if RemotePlayerRole == "HOST" then
                        tr:SetTextRenderColor({R = 255, G = 210, B = 40, A = 255}) -- Warm Gold
                    else
                        tr:SetTextRenderColor({R = 30, G = 220, B = 255, A = 255}) -- Neon Cyan
                    end
                end
            end)
            Log(string.format("[CO-OP] 3D Name Tag created: %s", NameTagActor:GetFullName()))
        end
    end

    return PuppetActor
end

-- ============================================================
-- 20 Hz Transform Sync & Animation Driver (Crash-Proof)
-- ============================================================
local function SyncLocalPlayerState()
    local player = GetLocalPlayer()
    if not player or not player:IsValid() then return end

    local loc = player:K2_GetActorLocation()
    local rot = player:K2_GetActorRotation()
    if not loc or not rot then return end

    -- Actor location is the capsule centre; send feet position so the puppet stands on the ground
    local halfHeight = 0.0
    pcall(function() halfHeight = player.CapsuleComponent:GetScaledCapsuleHalfHeight() end)

    local stateStr = string.format("%.2f %.2f %.2f %.2f %.2f %.2f", loc.X, loc.Y, loc.Z - halfHeight, rot.Pitch, rot.Yaw, rot.Roll)
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

    -- Lazy spawn remote puppet if not present
    if not PuppetActor or not PuppetActor:IsValid() then
        local now = os.time()
        if IsInGameplayWorld() and (now - LastSpawnAttempt >= 2) then
            LastSpawnAttempt = now
            SpawnRemotePuppet(World, {X = x, Y = y, Z = z}, {Pitch = pitch, Yaw = yaw, Roll = roll})
        end
    end

    if PuppetActor and PuppetActor:IsValid() then
        local newLoc = {X = x, Y = y, Z = z - PuppetMeshOffsetZ}
        local newRot = {Pitch = pitch, Yaw = yaw, Roll = roll}

        -- CRITICAL CRASH FIX: Always pass empty table {} for SweepHitResult, NEVER nil!
        pcall(function()
            PuppetActor:K2_SetActorLocationAndRotation(newLoc, newRot, false, {}, false)
        end)

        -- Calculate displacement speed to drive Walk/Idle animations
        local dx = x - LastPuppetX
        local dy = y - LastPuppetY
        local distMoved = math.sqrt(dx * dx + dy * dy)
        LastPuppetX = x
        LastPuppetY = y

        local skComp = PuppetActor.SkeletalMeshComponent or PuppetActor.Body
        if skComp and skComp:IsValid() then
            if distMoved > 2.0 then
                if not IsPuppetWalking and CachedWalkAnim and CachedWalkAnim:IsValid() then
                    IsPuppetWalking = true
                    pcall(function() skComp:PlayAnimation(CachedWalkAnim, true) end)
                end
            else
                if IsPuppetWalking and CachedIdleAnim and CachedIdleAnim:IsValid() then
                    IsPuppetWalking = false
                    pcall(function() skComp:PlayAnimation(CachedIdleAnim, true) end)
                end
            end
        end

        -- Update 3D Floating Billboard Name Tag
        if NameTagActor and NameTagActor:IsValid() then
            local tagLoc = {X = x, Y = y, Z = z + NAMETAG_HEIGHT}
            local tagYaw = yaw
            local localPlayer = GetLocalPlayer()
            if localPlayer and localPlayer:IsValid() then
                local pLoc = localPlayer:K2_GetActorLocation()
                if pLoc then
                    local vX = pLoc.X - x
                    local vY = pLoc.Y - y
                    tagYaw = math.atan(vY, vX) * (180.0 / math.pi)
                end
            end
            pcall(function()
                NameTagActor:K2_SetActorLocationAndRotation(tagLoc, {Pitch = 0.0, Yaw = tagYaw, Roll = 0.0}, false, {}, false)
            end)
        end
    end
end

-- ============================================================
-- Guest Game Logic Authority Suppression
-- ============================================================
local function ApplyGuestSuppression()
    if Role == "guest" then
        local aiManagers = FindAllOf("GSSAIManager_BP_C") or FindAllOf("AIManager") or {}
        for _, mgr in ipairs(aiManagers) do
            if mgr:IsValid() then mgr:SetActorTickEnabled(false) end
        end
    end
end

-- ============================================================
-- Event Synchronization Layer
-- ============================================================
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

        elseif cmd == "TIME" and Role == "guest" then
            local h, m, d, tod, skyTod = args:match("(%-?%d+)%s+(%-?%d+)%s+(%-?%d+)%s+([%d.-]+)%s+([%d.-]+)")
            if not h then return end
            local World = GetCurrentWorld()
            local gs = World and World.GameState
            if gs and gs:IsValid() then
                pcall(function()
                    gs.TimeStruct = {Minutes = tonumber(m), Hours = tonumber(h), Days = tonumber(d), TimeOfDay = tonumber(tod)}
                end)
            end
            local sky = FindFirstOf("Ultra_Dynamic_Sky_BP_Paradise_Island_C") or FindFirstOf("Ultra_Dynamic_Sky_BP_C")
            if sky and sky:IsValid() and tonumber(skyTod) >= 0 then
                pcall(function()
                    sky["Animate Time of Day"] = false
                    sky["Time of Day"] = tonumber(skyTod)
                    local fRot = sky["Set Sun and Moon Rotation"]
                    if fRot then fRot(sky) end
                    local fMat = sky["Set Material Variables"]
                    if fMat then fMat(sky) end
                end)
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

-- 1 Hz Host Clock Sync (GSSGameState.TimeStruct drives the HUD clock, UDS "Time of Day" drives the sun)
local function SyncTimeLoop()
    if Role ~= "host" or not IsInGameplayWorld() then return end
    SafeExec(function()
        local World = GetCurrentWorld()
        local gs = World and World.GameState
        if not gs or not gs:IsValid() then return end
        local t = gs.TimeStruct
        local skyTod = -1.0
        local sky = FindFirstOf("Ultra_Dynamic_Sky_BP_Paradise_Island_C") or FindFirstOf("Ultra_Dynamic_Sky_BP_C")
        if sky and sky:IsValid() then
            pcall(function() skyTod = sky["Time of Day"] end)
        end
        SendEvent(string.format("TIME %d %d %d %.3f %.3f", t.Hours, t.Minutes, t.Days, t.TimeOfDay, skyTod))
    end)
end

-- ============================================================
-- In-Game Status HUD (Real-Time Handshake Feedback)
-- ============================================================
local function UpdateInGameHUD()
    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return end

    local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    if not Kismet or not Kismet:IsValid() then return end

    local isConnected = CheckPeerStatus()
    local banner = ""
    local color = {R = 0.0, G = 1.0, B = 0.5, A = 1.0}

    if IsInGameplayWorld() then
        if isConnected then
            banner = string.format("⭐ CO-OP CONNECTED | Partner: %s [%s] | Route 66 Station Synchronized", RemotePlayerName, RemotePlayerRole)
            color = {R = 0.0, G = 1.0, B = 0.6, A = 1.0}
        else
            if Role == "host" then
                banner = string.format("[CO-OP HOST] Waiting for partner to connect on port 7777... (Share your IP!)")
                color = {R = 1.0, G = 0.85, B = 0.2, A = 1.0}
            elseif Role == "guest" then
                banner = string.format("[CO-OP CLIENT] Connecting to Host station...")
                color = {R = 0.2, G = 0.8, B = 1.0, A = 1.0}
            end
        end
        if banner ~= "" then
            pcall(function()
                Kismet:PrintString(World, banner, true, false, color, 1.0)
            end)
        end
    elseif World:GetFullName():lower():find("menu") then
        if Role == "host" then
            banner = "[CO-OP HOST] Server active on port 7777! Entering station..."
            color = {R = 0.0, G = 1.0, B = 0.5, A = 1.0}
        elseif Role == "guest" then
            banner = "[CO-OP CLIENT] Synced with Host! Entering station..."
            color = {R = 0.2, G = 0.8, B = 1.0, A = 1.0}
        else
            banner = "GAS STATION CO-OP:  [F9] HOST A WORLD   |   [F8] JOIN A WORLD   |   (or click DLC on menu)"
            color = {R = 1.0, G = 0.85, B = 0.2, A = 1.0}
        end
        pcall(function()
            Kismet:PrintString(World, banner, true, false, color, 1.8)
        end)
    end
end

-- ============================================================
-- Robust Multi-Stage Station Level Entry Layer
-- ============================================================
local HasEnteredGameplay = false
local LevelAttemptCount = 0
local LastAttemptTime = 0
local LevelLoadInProgress = false
local LevelLoadStartTime = 0

local function TryTriggerLevelLoad(menu)
    local World = GetCurrentWorld()
    if not World or not World:IsValid() then return false end
    local wname = World:GetFullName():lower()

    if wname:find("demomapka") and GetLocalPlayer() ~= nil then
        if not HasEnteredGameplay then
            HasEnteredGameplay = true
            LevelLoadInProgress = false
            Log("[CO-OP] *** SUCCESSFULLY INSIDE STATION GAMEPLAY (DemoMapka)! ***")
        end
        return true
    end

    local now = os.time()
    if LevelLoadInProgress and (now - LevelLoadStartTime < 8) then
        return true
    end

    if not menu or not menu:IsValid() then
        local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
        if #menus > 0 and menus[1]:IsValid() then
            menu = menus[1]
        end
    end

    LevelAttemptCount = LevelAttemptCount + 1
    LevelLoadInProgress = true
    LevelLoadStartTime = now
    Log(string.format("[CO-OP] Station Level Load Attempt #%d (Role: %s)...", LevelAttemptCount, tostring(Role)))

    if menu and menu:IsValid() then
        local canLoad = false
        pcall(function() canLoad = menu.bCanBeLoaded end)

        if canLoad then
            Log("[CO-OP] [STAGE 1] Save slot confirmed! Clicking Continue Button...")
            local s, err = pcall(function()
                menu:BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature()
            end)
            if s then return true end
        end

        pcall(function()
            if menu.MapSelectionWidget and menu.MapSelectionWidget:IsValid() then
                local buttons = menu.MapSelectionWidget.MapsButtons
                if buttons and #buttons > 0 and buttons[1]:IsValid() then
                    pcall(function() buttons[1]:GamePadClick() end)
                    pcall(function() buttons[1]:BndEvt__WBP_MapSelectionButton_Button_22_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature() end)
                end
            end
        end)

        if LevelAttemptCount >= 5 and not canLoad then
            Log("[CO-OP] [STAGE 3] Triggering NewGameButton...")
            pcall(function()
                menu:BndEvt__NewGameButton_K2Node_ComponentBoundEvent_2_OnClicked__DelegateSignature()
                menu:StartNewGame()
            end)
        end
    end

    -- Stage 4: Console Fallback after 6 attempts
    if LevelAttemptCount >= 6 and World and World:IsValid() then
        Log("[CO-OP] [STAGE 4] Executing console fallback: open DemoMapka...")
        local Kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        if Kismet and Kismet:IsValid() then
            pcall(function()
                Kismet:ExecuteConsoleCommand(World, "open DemoMapka", nil)
            end)
        end
    end

    return false
end

-- Role Actions
local function ExecuteHostGame(menu)
    Log("[CO-OP] >>> OPTION 1: HOST A WORLD <<<")
    LockAndSetRole("host")
    StartHostRelay()
    TryTriggerLevelLoad(menu)
end

local function ExecuteJoinGame(menu, promptForIP)
    Log("[CO-OP] >>> OPTION 2: JOIN A WORLD <<<")
    local targetIP = "127.0.0.1"

    if promptForIP then
        -- Open dialog asynchronously (NO /wait so game thread never hangs)
        os.execute('start "" pythonw "coop_menu.py"')
    end

    local f = io.open("net/host_ip.txt", "r") or io.open("host_ip.txt", "r")
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

-- Hook Main Menu DLC Button Click
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
            -- Launch asynchronously without /wait
            os.execute('start "" pythonw "coop_menu.py"')
        end)
    end)
end)

-- ============================================================
-- Pause Menu & ESC Glitch Fix
-- ============================================================
local function RestoreGameplayInput()
    local pc = (UEHelpers and UEHelpers.GetPlayerController) and UEHelpers.GetPlayerController() or FindFirstOf("PlayerController")
    if pc and pc:IsValid() then
        pcall(function()
            pc.bShowMouseCursor = false
            pc.bEnableClickEvents = true
            pc.bEnableMouseOverEvents = true
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
        local player = GetLocalPlayer()
        if player and player:IsValid() then
            pcall(function()
                if player.SetDefaultWidgetInteraction then
                    player:SetDefaultWidgetInteraction()
                end
            end)
        end
    end
end

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

-- Dedicated Hotkeys
RegisterKeyBind(Key.F9, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteHostGame(menu)
end)

RegisterKeyBind(Key.F8, function()
    local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
    local menu = (#menus > 0 and menus[1]:IsValid()) and menus[1] or nil
    ExecuteJoinGame(menu, true)
end)

RegisterKeyBind(Key.F7, function()
    if not IsInGameplayWorld() then return end
    local f = io.open("net/remote_player.state", "r")
    if not f then return end
    local line = f:read("*line")
    f:close()
    if not line or line == "" then return end
    local x, y, z = line:match("([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)")
    if not x then return end
    local player = GetLocalPlayer()
    if player and player:IsValid() then
        ExecuteInGameThread(function()
            local targetLoc = {X = tonumber(x) + 100.0, Y = tonumber(y) + 100.0, Z = tonumber(z) + 10.0}
            player:K2_SetActorLocation(targetLoc, false, {}, false)
            Log(string.format("[CO-OP] Teleported to partner at (%.1f, %.1f, %.1f)", targetLoc.X, targetLoc.Y, targetLoc.Z))
        end)
    end
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
    EnsureBackgroundRelay()
    UpdateInGameHUD()
    SyncEconomyLoop()
    SyncTimeLoop()

    -- Check if world transitioned
    local World = GetCurrentWorld()
    if World and World:IsValid() then
        local wname = World:GetFullName():lower()
        if wname:find("demomapka") and GetLocalPlayer() ~= nil then
            if not HasEnteredGameplay then
                HasEnteredGameplay = true
                LevelLoadInProgress = false
                -- Console "open DemoMapka" bypasses the menu's own teardown, leaving the viewport in UI-only input
                ExecuteInGameThread(RestoreGameplayInput)
                Log("[CO-OP] *** CONNECTED TO GAS STATION WORLD! MULTIPLAYER SYNC RUNNING. ***")
            end
            return false
        else
            -- Left gameplay world -> invalidate cached actors
            if HasEnteredGameplay then
                HasEnteredGameplay = false
                PuppetActor = nil
                NameTagActor = nil
                CachedLocalPlayer = nil
            end
        end
    end

    -- Trigger level load if role selected and not yet in gameplay
    if (Role == "host" or Role == "guest") and not HasEnteredGameplay then
        local now = os.time()
        if now - LastAttemptTime >= 1 then
            LastAttemptTime = now
            ExecuteInGameThread(function()
                pcall(TryTriggerLevelLoad, nil)
            end)
        end
    end

    return false
end)

LoopAsync(3000, function()
    ApplyGuestSuppression()
    ReadLocalProfile()
    return false
end)

Log("GasStationCoop Engine v2.0 initialized. 3D Character Puppets, Floating Name Tags, and State Replication active.")
