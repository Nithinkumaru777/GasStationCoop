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

local GetLocalPlayer -- defined below; the player's own world is the only reliable "current" world

local function GetCurrentWorld()
    -- FindAllOf("World") also returns the menu world still waiting for GC, which made the
    -- host think it never left the menu and re-run "open DemoMapka" every 8 seconds.
    local player = GetLocalPlayer()
    if player then
        local ok, w = pcall(function() return player:GetWorld() end)
        if ok and w and w:IsValid() then return w end
    end
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
GetLocalPlayer = function()
    if CachedLocalPlayer and CachedLocalPlayer:IsValid() then
        return CachedLocalPlayer
    end
    CachedLocalPlayer = nil
    -- Only accept the pawn that lives in the station map (stale pawns from a torn-down world don't count)
    for _, p in ipairs(FindAllOf("PlayerCharacter_BP_C") or {}) do
        if p:IsValid() and p:GetFullName():lower():find("demomapka") then
            CachedLocalPlayer = p
            break
        end
    end
    return CachedLocalPlayer
end

local function IsInGameplayWorld()
    return GetLocalPlayer() ~= nil
end

local function GetLocalController()
    local player = GetLocalPlayer()
    if not player then return nil end
    local pc = nil
    pcall(function() pc = player.Controller end)
    if pc and pc:IsValid() then return pc end
    return nil
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

-- Candidates per state; the first whose Skeleton matches the puppet mesh wins (a mismatch renders as a T-pose)
local AnimCandidates = {
    walk = {
        "/Game/Assets/Characters/NewBaseMesh/Animations/Movement/WalkFwdLoop.WalkFwdLoop",
        "/Game/Assets/Characters/Animations/NPCs/Movement/Cleaning/IPC/BaseNPC_Walk_F_IP_02.BaseNPC_Walk_F_IP_02",
        "/Game/Assets/Characters/NewBaseMesh/Animations/Party/ma_DancePeople_Walk_01_anim.ma_DancePeople_Walk_01_anim",
    },
    idle = {
        "/Game/Assets/Characters/NewBaseMesh/Animations/Movement/Base_Idle_Male_00.Base_Idle_Male_00",
        "/Game/Assets/Characters/NewBaseMesh/Animations/Idles/Idle_01_LookAround.Idle_01_LookAround",
        "/Game/Assets/Characters/Animations/NPCs/Movement/Cleaning/IPC/BaseNPC_Standing_Idle_00.BaseNPC_Standing_Idle_00",
        "/Game/Assets/Characters/Animations/NPCs/Movement/IPC/Idle_01_LookAround.Idle_01_LookAround",
    },
}
-- Used when no candidate fits the chosen archetype's skeleton
local FALLBACK_BODY = "/Game/Assets/Characters/NewBaseMesh/DeliveryGuys/SK_Ma_GasolineDelivery_T.SK_Ma_GasolineDelivery_T"

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

local function SkeletonName(obj)
    local name = nil
    pcall(function() name = obj.Skeleton:GetFullName() end)
    return name
end

local function PickAnim(list, meshSkel)
    for _, path in ipairs(list) do
        local anim = FindOrLoad(path)
        if anim and SkeletonName(anim) == meshSkel then return anim end
    end
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
local PuppetStillTicks = 0
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

            -- Pick animations built for this mesh's skeleton (PlayAnimation switches to SingleNode mode itself)
            local meshSkel = SkeletonName(skComp.SkeletalMesh)
            CachedIdleAnim = PickAnim(AnimCandidates.idle, meshSkel)
            CachedWalkAnim = PickAnim(AnimCandidates.walk, meshSkel)
            if not CachedIdleAnim then
                local fallback = FindOrLoad(FALLBACK_BODY)
                if fallback then
                    Log(string.format("[CO-OP] No animation fits skeleton %s; switching puppet body to %s", tostring(meshSkel), FALLBACK_BODY))
                    skComp:SetSkeletalMesh(fallback, true)
                    if head and head:IsValid() then pcall(function() head:SetVisibility(false, false) end) end
                    meshSkel = SkeletonName(fallback)
                    CachedIdleAnim = PickAnim(AnimCandidates.idle, meshSkel)
                    CachedWalkAnim = PickAnim(AnimCandidates.walk, meshSkel)
                end
            end
            CachedWalkAnim = CachedWalkAnim or CachedIdleAnim
            Log(string.format("[CO-OP] Puppet skeleton %s | idle=%s walk=%s", tostring(meshSkel),
                CachedIdleAnim and CachedIdleAnim:GetFullName() or "NONE", CachedWalkAnim and CachedWalkAnim:GetFullName() or "NONE"))
            if CachedIdleAnim then
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
                    -- Plain ASCII: the TextRender font has no emoji glyphs (rendered as a box)
                    local label = string.format("%s [%s]", RemotePlayerName, RemotePlayerRole)
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
                PuppetStillTicks = 0
                if not IsPuppetWalking and CachedWalkAnim and CachedWalkAnim:IsValid() then
                    IsPuppetWalking = true
                    pcall(function() skComp:PlayAnimation(CachedWalkAnim, true) end)
                end
            else
                -- Relay updates arrive with gaps; only idle after ~300 ms without movement to avoid flicker
                PuppetStillTicks = PuppetStillTicks + 1
                if IsPuppetWalking and PuppetStillTicks >= 6 and CachedIdleAnim and CachedIdleAnim:IsValid() then
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
-- Event Synchronization Layer
-- ============================================================
-- The host's world is authoritative for customers, cars and trash (streamed to the guest as proxies).
-- Shared both ways: wallet, questline objectives. Host -> guest: clock/sky.
local function SendEvent(eventLine)
    local f = io.open("net/events.out", "a")
    if f then f:write(eventLine .. "\n") f:close() end
end

local RemoteRegisterLocked = false
local LastSyncedMoney = nil

-- ============================================================
-- Shared Questline Objectives
-- ============================================================
-- Objectives are identified by their Blueprint class path, which is identical in both games
-- (instance names are runtime-generated). Known gap: switching the followed questline looks like a completion.
local LastObjectivePath = nil
local LastObjectiveProgress = -1
local RecentDone = {}       -- objectives this side finished, re-sent periodically (UDP can drop packets)
local PendingRemoteDone = {} -- partner finished these; finish locally as soon as we reach them

-- "ClassName /Game/Path.Asset" -> "/Game/Path.Asset"
local function PathOf(obj)
    local full = obj:GetFullName()
    return full:match("^%S+%s+(.+)$") or full
end

local function ObjectPath(obj)
    return PathOf(obj:GetClass())
end

local function ResetQuestTracking()
    LastObjectivePath = nil
    LastObjectiveProgress = -1
end

local function GetActiveObjective()
    for _, qs in ipairs(FindAllOf("QuestSubsystem") or {}) do
        if qs:IsValid() then
            local obj = nil
            pcall(function()
                local line = qs:GetFollowedQuestLine()
                if line and line:IsValid() then obj = line.ActiveObjective end
            end)
            if obj and obj:IsValid() then return obj end
        end
    end
    return nil
end

local function FinishObjectiveFromPartner(obj, path)
    PendingRemoteDone[path] = nil
    Log("[QUEST] Partner completed objective, completing locally: " .. path)
    LastObjectivePath = nil -- don't echo this completion back as our own
    pcall(function() obj:FinishObjective() end)
end

local function SyncQuestLoop()
    local obj = GetActiveObjective()
    local path = obj and ObjectPath(obj) or nil

    if path ~= LastObjectivePath then
        -- The objective we were on is gone: we completed it locally
        if LastObjectivePath and not PendingRemoteDone[LastObjectivePath] then
            table.insert(RecentDone, LastObjectivePath)
            if #RecentDone > 5 then table.remove(RecentDone, 1) end
            SendEvent("OBJ_DONE " .. LastObjectivePath)
            Log("[QUEST] Objective completed, shared with partner: " .. LastObjectivePath)
        end
        LastObjectivePath = path
        LastObjectiveProgress = -1
    end
    if not obj then return end

    if PendingRemoteDone[path] then
        FinishObjectiveFromPartner(obj, path)
        return
    end

    -- Countable objectives ("serve 5 customers"): share the higher progress
    local progress = nil
    pcall(function() progress = obj.CurrentProgress end)
    if type(progress) == "number" and progress > LastObjectiveProgress then
        if LastObjectiveProgress >= 0 then SendEvent(string.format("OBJ_PROGRESS %d %s", progress, path)) end
        LastObjectiveProgress = progress
    end
end

local function ResendRecentObjectives()
    for _, p in ipairs(RecentDone) do SendEvent("OBJ_DONE " .. p) end
end

-- Shared wallet: host owns the balance; guest reports its own earnings/spending as deltas
local LastAppliedHostMoney = nil
local function ReportGuestMoneyDelta()
    local pc = GetLocalController()
    if not pc or LastAppliedHostMoney == nil then return end
    local cur = nil
    pcall(function() cur = pc:GetMoney() end)
    if cur and math.abs(cur - LastAppliedHostMoney) >= 0.05 then
        SendEvent(string.format("ADD_MONEY %.2f", cur - LastAppliedHostMoney))
        LastAppliedHostMoney = cur
    end
end

-- ============================================================
-- Host-Authoritative World Replication (customers, cars, trash)
-- ============================================================
-- The host streams every customer, car and trash item (meshes once, transforms at 10 Hz).
-- The guest switches off its own AI spawning, removes its local copies and renders
-- mesh-only proxies that follow the host's actors.
local ENTITY_KINDS = {
    {kind = "npc", class = "AICharacterBase", comp = "SkeletalMeshComponent", meshProp = "SkeletalMesh", maxParts = 6},
    {kind = "car", class = "GSSWheeledVehicle", comp = "SkeletalMeshComponent", meshProp = "SkeletalMesh", maxParts = 3},
    {kind = "trash", class = "TrashItemBase", comp = "StaticMeshComponent", meshProp = "StaticMesh", maxParts = 1},
}
local MAX_ENTITIES = 80   -- keeps ENT_ROSTER under the relay's 4 KB receive buffer
local MAX_LINE = 1200     -- one event line = one UDP datagram; stay under a typical MTU
local HostEntities = {}   -- id -> {actor, kind, comp, meshes, last, announced}
local HostEntityCount = 0
local Proxies = {}        -- id -> {kind, meshes, parts, body, target, cur, idle, walk, walking, still}

local function ActorId(actor)
    local id = nil
    pcall(function() id = actor:GetFName():ToString() end)
    return id
end

-- The player's own trucks (Rudy/Towy) are local to each world and never replicated or removed
local function PlayerVehicleSet()
    local set = {}
    for _, v in ipairs(FindAllOf("PlayerVehicle") or {}) do
        if v:IsValid() then set[v:GetFullName()] = true end
    end
    return set
end

local function EachEntityActor(fn)
    local skipCars = PlayerVehicleSet()
    for _, def in ipairs(ENTITY_KINDS) do
        for _, actor in ipairs(FindAllOf(def.class) or {}) do
            if actor:IsValid() and not (def.kind == "car" and skipCars[actor:GetFullName()]) then
                fn(actor, def)
            end
        end
    end
end

-- Visible mesh components of an actor (pawn/vehicle Mesh first) and their mesh asset paths
local function CollectMeshes(actor, def)
    local comps, seen = {}, {}
    local function add(c)
        if #comps >= def.maxParts or not c or not c:IsValid() then return end
        local key = c:GetFullName()
        if seen[key] then return end
        local visible = true
        pcall(function() visible = c:IsVisible() end)
        local mesh = c[def.meshProp]
        if visible and mesh and mesh:IsValid() then
            seen[key] = true
            table.insert(comps, {comp = c, path = PathOf(mesh)})
        end
    end
    pcall(function() add(actor.Mesh) end)
    local compClass = StaticFindObject("/Script/Engine." .. def.comp)
    pcall(function()
        actor:K2_GetComponentsByClass(compClass):ForEach(function(_, elem) add(elem:get()) end)
    end)
    return comps
end

local function HostScanEntities()
    local seen = {}
    EachEntityActor(function(actor, def)
        local id = ActorId(actor)
        if not id then return end
        seen[id] = true
        if HostEntities[id] or HostEntityCount >= MAX_ENTITIES then return end
        local comps = CollectMeshes(actor, def)
        if #comps == 0 then return end
        local meshes = {}
        for _, c in ipairs(comps) do table.insert(meshes, c.path) end
        HostEntities[id] = {actor = actor, kind = def.kind, comp = comps[1].comp, meshes = meshes}
        HostEntityCount = HostEntityCount + 1
    end)
    for id, e in pairs(HostEntities) do
        if not seen[id] or not e.actor:IsValid() then
            HostEntities[id] = nil
            HostEntityCount = HostEntityCount - 1
            SendEvent("ENT_DEL " .. id)
        end
    end
end

-- Sends the primary mesh component's world transform (already includes the pawn's mesh offset)
local function HostSendTransforms(force)
    local chunk, len = {}, 0
    local function flush()
        if #chunk > 0 then SendEvent("ENTS " .. table.concat(chunk, ";")) end
        chunk, len = {}, 0
    end
    for id, e in pairs(HostEntities) do
        if not e.announced then
            SendEvent(string.format("ENT_NEW %s %s %s", id, e.kind, table.concat(e.meshes, "|")))
            e.announced = true
        end
        local s = nil
        pcall(function()
            local l, r = e.comp:K2_GetComponentLocation(), e.comp:K2_GetComponentRotation()
            local last = e.last
            if force or not last or math.abs(l.X - last.X) + math.abs(l.Y - last.Y) + math.abs(l.Z - last.Z) > 1.0
                or math.abs(r.Yaw - last.Yaw) > 1.0 then
                e.last = {X = l.X, Y = l.Y, Z = l.Z, Yaw = r.Yaw}
                s = string.format("%s %.1f %.1f %.1f %.1f %.1f %.1f", id, l.X, l.Y, l.Z, r.Pitch, r.Yaw, r.Roll)
            end
        end)
        if s then
            if len + #s + 1 > MAX_LINE then flush() end
            table.insert(chunk, s)
            len = len + #s + 1
        end
    end
    flush()
end

-- Every few seconds: full roster + re-announce, so a guest that joined late or lost packets heals
local function HostSendRoster()
    local ids = {}
    for id, e in pairs(HostEntities) do
        table.insert(ids, id)
        e.announced = false
    end
    SendEvent("ENT_ROSTER " .. table.concat(ids, ","))
    HostSendTransforms(true)
end

local function DestroyProxy(p)
    for _, a in ipairs(p.parts or {}) do
        pcall(function() if a:IsValid() then a:K2_DestroyActor() end end)
    end
    p.parts = nil
end

local function SpawnProxy(p)
    local World = GetCurrentWorld()
    if not World then return end
    local t = p.target
    local loc = {X = t.X, Y = t.Y, Z = t.Z}
    local rot = {Pitch = t.Pitch, Yaw = t.Yaw, Roll = t.Roll}
    local isStatic = (p.kind == "trash")
    local cls = StaticFindObject(isStatic and "/Script/Engine.StaticMeshActor" or "/Script/Engine.SkeletalMeshActor")
    p.parts = {}
    for _, path in ipairs(p.meshes) do
        local mesh = FindOrLoad(path)
        local a = mesh and SpawnActorFromClass(World, cls, loc, rot)
        if a and a:IsValid() then
            pcall(function()
                a:SetActorEnableCollision(false)
                local c = isStatic and a.StaticMeshComponent or a.SkeletalMeshComponent
                pcall(function() c:SetMobility(2) end) -- Movable, or K2_SetActorLocation is ignored
                pcall(function() c:SetCollisionEnabled(0) end)
                if isStatic then c:SetStaticMesh(mesh) else c:SetSkeletalMesh(mesh, true) end
                -- Extra character parts (head, hair, clothes) follow the body's pose
                if p.body then c:SetMasterPoseComponent(p.body, true) else p.body = c end
            end)
            table.insert(p.parts, a)
        end
    end
    if p.kind == "npc" and p.body then
        local skel = SkeletonName(p.body.SkeletalMesh)
        p.idle = PickAnim(AnimCandidates.idle, skel)
        p.walk = PickAnim(AnimCandidates.walk, skel) or p.idle
        if p.idle then pcall(function() p.body:PlayAnimation(p.idle, true) end) end
    end
    p.cur = {X = t.X, Y = t.Y, Z = t.Z, Pitch = t.Pitch, Yaw = t.Yaw, Roll = t.Roll}
    p.walking, p.still = false, 0
end

local function LerpAngle(a, b, f)
    return a + ((b - a + 180) % 360 - 180) * f
end

-- Guest, 20 Hz: smooth proxies toward the host's latest 10 Hz transforms
local function DriveProxies()
    for _, p in pairs(Proxies) do
        if p.target and not p.parts then SpawnProxy(p) end
        if p.parts and p.cur then
            local c, t = p.cur, p.target
            local dx, dy, dz = t.X - c.X, t.Y - c.Y, t.Z - c.Z
            local dYaw = math.abs((t.Yaw - c.Yaw + 180) % 360 - 180)
            if math.abs(dx) + math.abs(dy) + math.abs(dz) > 0.05 or dYaw > 0.05 then
                local f = (dx * dx + dy * dy > 1000 * 1000) and 1.0 or 0.35 -- snap on teleports
                c.X, c.Y, c.Z = c.X + dx * f, c.Y + dy * f, c.Z + dz * f
                c.Pitch, c.Yaw, c.Roll = LerpAngle(c.Pitch, t.Pitch, f), LerpAngle(c.Yaw, t.Yaw, f), LerpAngle(c.Roll, t.Roll, f)
                local loc = {X = c.X, Y = c.Y, Z = c.Z}
                local rot = {Pitch = c.Pitch, Yaw = c.Yaw, Roll = c.Roll}
                for _, part in ipairs(p.parts) do
                    pcall(function() part:K2_SetActorLocationAndRotation(loc, rot, false, {}, false) end)
                end
            end
            if p.kind == "npc" and p.body and p.walk then
                if dx * dx + dy * dy > 25 then
                    p.still = 0
                    if not p.walking then
                        p.walking = true
                        pcall(function() p.body:PlayAnimation(p.walk, true) end)
                    end
                else
                    p.still = p.still + 1
                    if p.walking and p.still >= 6 then
                        p.walking = false
                        pcall(function() p.body:PlayAnimation(p.idle, true) end)
                    end
                end
            end
        end
    end
end

local function ClearProxies()
    for id, p in pairs(Proxies) do
        DestroyProxy(p)
        Proxies[id] = nil
    end
end

-- Guest: stop the local AI director and remove everything it already spawned
local function SuppressGuestWorld()
    for _, mgr in ipairs(FindAllOf("AIManager") or {}) do
        pcall(function() mgr.MaxVehiclesOnMap = 0 end)
        pcall(function() mgr:SetComponentTickEnabled(false) end)
    end
    for _, sp in ipairs(FindAllOf("AISpawnPoint") or {}) do
        pcall(function() sp:SetActorTickEnabled(false) end)
    end
    local removed = 0
    EachEntityActor(function(actor)
        pcall(function() actor:K2_DestroyActor() end)
        removed = removed + 1
    end)
    if removed > 0 then Log(string.format("[WORLD] Removed %d local guest actors (host world is authoritative)", removed)) end
end

local function HandleCoopEvent(cmd, args)
    SafeExec(function()
        if cmd == "MONEY" and Role == "guest" then
            local targetMoney = tonumber(args)
            local pc = GetLocalController()
            if targetMoney and pc then
                -- Report our own earnings/spending first so the host balance doesn't erase them
                ReportGuestMoneyDelta()
                local cur = pc:GetMoney()
                local delta = targetMoney - cur
                if math.abs(delta) >= 0.05 then
                    pcall(function() pc:Cheat_AddMoney(delta) end)
                end
                LastAppliedHostMoney = targetMoney
            end

        elseif cmd == "ADD_MONEY" then
            local amount = tonumber(args)
            local pc = GetLocalController()
            if amount and Role == "host" and pc then
                pcall(function() pc:Cheat_AddMoney(amount) end)
            end

        elseif cmd == "OBJ_DONE" then
            local path = args:match("^%s*(%S+)")
            if path and IsInGameplayWorld() then
                local obj = GetActiveObjective()
                if obj and ObjectPath(obj) == path then
                    FinishObjectiveFromPartner(obj, path)
                elseif not PendingRemoteDone[path] then
                    PendingRemoteDone[path] = true
                    Log("[QUEST] Partner completed objective (will apply when reached): " .. path)
                end
            end

        elseif cmd == "OBJ_PROGRESS" then
            local value, path = args:match("^(%d+)%s+(%S+)")
            value = tonumber(value)
            if value and IsInGameplayWorld() then
                local obj = GetActiveObjective()
                if obj and ObjectPath(obj) == path then
                    local cur = 0
                    pcall(function() cur = obj.CurrentProgress end)
                    if value > cur then
                        LastObjectiveProgress = value -- partner's progress, don't echo it back
                        pcall(function() obj:SetObjectiveProgress(value, true) end)
                    end
                end
            end

        elseif cmd == "REGISTER_LOCK" then
            RemoteRegisterLocked = true

        elseif cmd == "REGISTER_UNLOCK" then
            RemoteRegisterLocked = false

        elseif cmd == "FUEL_DONE" then
            Log(string.format("Partner completed fueling: %s", tostring(args)))

        elseif cmd == "ENT_NEW" and Role == "guest" then
            local id, kind, meshes = args:match("^(%S+)%s+(%a+)%s+(%S+)")
            if id and not Proxies[id] then
                local list = {}
                for m in meshes:gmatch("[^|]+") do table.insert(list, m) end
                Proxies[id] = {kind = kind, meshes = list}
            end

        elseif cmd == "ENTS" and Role == "guest" then
            for entry in args:gmatch("[^;]+") do
                local id, x, y, z, p, yw, r = entry:match("^%s*(%S+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)%s+([%d.-]+)")
                local proxy = id and Proxies[id]
                if proxy then
                    proxy.target = {X = tonumber(x), Y = tonumber(y), Z = tonumber(z), Pitch = tonumber(p), Yaw = tonumber(yw), Roll = tonumber(r)}
                end
            end

        elseif cmd == "ENT_DEL" and Role == "guest" then
            local id = args:match("^%s*(%S+)")
            if id and Proxies[id] then
                DestroyProxy(Proxies[id])
                Proxies[id] = nil
            end

        elseif cmd == "ENT_ROSTER" and Role == "guest" then
            local alive = {}
            for id in args:gmatch("[^,%s]+") do alive[id] = true end
            for id, p in pairs(Proxies) do
                if not alive[id] then
                    DestroyProxy(p)
                    Proxies[id] = nil
                end
            end

        elseif cmd == "GUEST_TRASH" and Role == "host" then
            local id = args:match("^%s*(%S+)")
            local e = id and HostEntities[id]
            if e and e.kind == "trash" and e.actor:IsValid() then
                Log("[WORLD] Partner picked up trash: " .. id)
                pcall(function() e.actor:K2_DestroyActor() end)
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
-- Runs on the game thread (called from the 1 Hz loop's SafeExec)
local EconomyTick = 0
local function SyncEconomyLoop()
    if Role == "guest" then
        ReportGuestMoneyDelta()
        return
    end
    if Role ~= "host" then return end
    local pc = GetLocalController()
    if not pc then return end
    local money = nil
    pcall(function() money = pc:GetMoney() end)
    if not money then return end
    -- Re-send every 5 s even when unchanged so a guest that (re)joins or dropped a packet catches up
    EconomyTick = EconomyTick + 1
    if LastSyncedMoney == nil or math.abs(money - LastSyncedMoney) >= 0.05 or EconomyTick % 5 == 0 then
        LastSyncedMoney = money
        SendEvent(string.format("MONEY %.2f", money))
    end
end

-- 1 Hz Host Clock Sync (GSSGameState.TimeStruct drives the HUD clock, UDS "Time of Day" drives the sun)
local function SyncTimeLoop()
    if Role ~= "host" then return end
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
            banner = string.format("CO-OP CONNECTED | Partner: %s [%s] | Route 66 Station Synchronized", RemotePlayerName, RemotePlayerRole)
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
local LevelLoadInProgress = false
local LevelLoadStartTime = 0

local function TryTriggerLevelLoad(menu)
    if IsInGameplayWorld() then
        if not HasEnteredGameplay then
            HasEnteredGameplay = true
            LevelLoadInProgress = false
            Log("[CO-OP] *** SUCCESSFULLY INSIDE STATION GAMEPLAY (DemoMapka)! ***")
        end
        return true
    end

    local now = os.time()
    -- The station map takes a while to stream in; don't click again mid-load
    if LevelLoadInProgress and (now - LevelLoadStartTime < 20) then
        return true
    end

    if not menu or not menu:IsValid() then
        local menus = FindAllOf("MainMenuOverviewWidgetBP_C") or {}
        if #menus > 0 and menus[1]:IsValid() then
            menu = menus[1]
        end
    end
    -- No main menu = loading screen or intro; wait instead of forcing a level change
    if not menu or not menu:IsValid() then return false end

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

        if LevelAttemptCount >= 2 and not canLoad then
            Log("[CO-OP] [STAGE 2] No save to continue, starting a New Game...")
            pcall(function() menu:StartNewGame() end)
        end
    end

    -- No raw "open DemoMapka" fallback: it skips the game's own init (no HUD, quests, input, clock),
    -- which is exactly the broken guest world. If the menu path fails, the player can click Play manually.
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
    local pc = GetLocalController()
    if pc then
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

-- Guest: F next to a host trash item picks it up in the host's world
RegisterKeyBind(Key.F, function()
    if Role ~= "guest" then return end
    SafeExec(function()
        local player = GetLocalPlayer()
        if not player then return end
        local pl = player:K2_GetActorLocation()
        local best, bestD = nil, 250.0 * 250.0
        for id, p in pairs(Proxies) do
            if p.kind == "trash" and p.cur then
                local dx, dy, dz = p.cur.X - pl.X, p.cur.Y - pl.Y, p.cur.Z - pl.Z
                local d = dx * dx + dy * dy + dz * dz
                if d < bestD then best, bestD = id, d end
            end
        end
        if best then
            SendEvent("GUEST_TRASH " .. best)
            DestroyProxy(Proxies[best])
            Proxies[best] = nil
        end
    end)
end)

-- Loops
LoopAsync(50, function()
    SafeExec(function()
        SyncLocalPlayerState()
        DriveRemotePuppet()
        ProcessIncomingEvents()
        if Role == "guest" and IsInGameplayWorld() then DriveProxies() end
    end)
    return false
end)

-- Host, 10 Hz: stream customer/car/trash transforms (only while a partner is listening,
-- otherwise the relay never drains events.out)
LoopAsync(100, function()
    SafeExec(function()
        if Role == "host" and IsInGameplayWorld() and CheckPeerStatus() then HostSendTransforms(false) end
    end)
    return false
end)

-- Every UObject access happens on the game thread. Touching UObjects from the LoopAsync thread
-- during a level transition hung that thread and silently killed all sync (host log stopped dead).
local SlowTick = 0
LoopAsync(1000, function()
    EnsureBackgroundRelay()
    SafeExec(function()
        UpdateInGameHUD()

        if IsInGameplayWorld() then
            if not HasEnteredGameplay then
                HasEnteredGameplay = true
                LevelLoadInProgress = false
                RestoreGameplayInput()
                ResetQuestTracking()
                Log("[CO-OP] *** CONNECTED TO GAS STATION WORLD! MULTIPLAYER SYNC RUNNING. ***")
            end
            SyncEconomyLoop()
            SyncTimeLoop()
            SyncQuestLoop()
            SlowTick = SlowTick + 1
            if SlowTick % 3 == 0 then ResendRecentObjectives() end
            if Role == "host" and CheckPeerStatus() then
                HostScanEntities()
                if SlowTick % 5 == 0 then HostSendRoster() end
                -- 0 here in a busy station means FindAllOf(base class) isn't matching Blueprint subclasses
                if SlowTick % 30 == 0 then Log(string.format("[WORLD] Streaming %d customers/cars/trash to partner", HostEntityCount)) end
            elseif Role == "guest" and SlowTick % 2 == 0 then
                SuppressGuestWorld()
            end
        else
            -- Left gameplay world -> invalidate cached actors
            if HasEnteredGameplay then
                HasEnteredGameplay = false
                PuppetActor = nil
                NameTagActor = nil
                CachedLocalPlayer = nil
                ResetQuestTracking()
                ClearProxies()
                HostEntities, HostEntityCount = {}, 0
            end
            if Role == "host" or Role == "guest" then
                TryTriggerLevelLoad(nil)
            end
        end
    end)
    return false
end)

LoopAsync(3000, function()
    ReadLocalProfile()
    return false
end)

Log("GasStationCoop Engine v2.0 initialized. 3D Character Puppets, Floating Name Tags, and State Replication active.")
