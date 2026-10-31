-- Minimal fake of the UE4SS Lua API + the GSS objects main.lua touches.
-- FAKE is the test handle used by the Python harness.
FAKE = { logs = {}, loops = {}, console = {}, inGame = false }

os.execute = function(cmd) return true end
print = function(s) table.insert(FAKE.logs, tostring(s)) end
ExecuteInGameThread = function(fn) fn() end
LoopAsync = function(ms, fn) table.insert(FAKE.loops, {ms = ms, fn = fn}) end
RegisterHook = function() end
FAKE.keys = {}
RegisterKeyBind = function(key, fn) FAKE.keys[key] = fn end
Key = setmetatable({}, {__index = function(_, k) return k end})

local function obj(class, path, t)
    t = t or {}
    t._class, t._path = class, path
    t.IsValid = function() return true end
    t.GetFullName = function(self) return self._class .. " " .. self._path end
    t.GetClass = function(self)
        return { GetFullName = function() return "BlueprintGeneratedClass " .. self._classPath end }
    end
    return t
end
FAKE.obj = obj

-- Skeletons: biker body has its own skeleton, NewBaseMesh anims + fallback body share another
local SK_BIKER = obj("Skeleton", "/Game/Biker_Skeleton")
local SK_BASE = obj("Skeleton", "/Game/ma_baseMesh_final_SK_Skeleton")
local assets = {}
local function asset(path, skel) assets[path] = obj("Asset", path, {Skeleton = skel}) end
asset("/Game/Assets/Characters/Biker/biker_body_SK.biker_body_SK", SK_BIKER)
asset("/Game/Assets/Characters/NewBaseMesh/DeliveryGuys/SK_Ma_GasolineDelivery_T.SK_Ma_GasolineDelivery_T", SK_BASE)
asset("/Game/Assets/Characters/NewBaseMesh/Animations/Movement/WalkFwdLoop.WalkFwdLoop", SK_BASE)
asset("/Game/Assets/Characters/NewBaseMesh/Animations/Movement/Base_Idle_Male_00.Base_Idle_Male_00", SK_BASE)
asset("/Game/Assets/Characters/Animations/NPCs/Movement/Cleaning/IPC/BaseNPC_Standing_Idle_00.BaseNPC_Standing_Idle_00", obj("Skeleton", "/Game/NPC_Base_Skeleton"))

-- Spawnable actors
FAKE.spawned = {}
local function newActor(kind, loc)
    local a = obj(kind, "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel." .. kind .. "_" .. #FAKE.spawned)
    a.loc = {X = loc.X, Y = loc.Y, Z = loc.Z}
    a.SetActorEnableCollision = function() end
    a.K2_GetActorLocation = function(self) return self.loc end
    a.K2_SetActorLocationAndRotation = function(self, l, r, sweep, hit, tp)
        assert(type(hit) == "table", "SweepHitResult must be a table")
        self.loc = l
    end
    if kind == "Biker_ActorBp_C" then
        a.Body = obj("SkeletalMeshComponent", a._path .. ".Body", {
            SkeletalMesh = assets["/Game/Assets/Characters/Biker/biker_body_SK.biker_body_SK"],
            SetCollisionEnabled = function() end,
            SetSkeletalMesh = function(self, m) self.SkeletalMesh = m end,
            SetWorldScale3D = function() end,
            PlayAnimation = function(self, anim) self.playing = anim end,
            K2_GetComponentLocation = function() return {X = a.loc.X, Y = a.loc.Y, Z = a.loc.Z - 90} end,
        })
        a.Head = obj("SkeletalMeshComponent", a._path .. ".Head", {
            SetMasterPoseComponent = function() end,
            SetVisibility = function(self, v) self.visible = v end,
        })
    elseif kind == "SkeletalMeshActor" or kind == "StaticMeshActor" then
        local c = obj("MeshComponent", a._path .. ".Root", {
            SetMobility = function(self, m) self.mobility = m end,
            SetCollisionEnabled = function() end,
            SetSkeletalMesh = function(self, m) self.SkeletalMesh = m end,
            SetStaticMesh = function(self, m) self.StaticMesh = m end,
            SetMasterPoseComponent = function(self, leader) self.leader = leader end,
            PlayAnimation = function(self, anim) self.playing = anim end,
        })
        if kind == "SkeletalMeshActor" then a.SkeletalMeshComponent = c else a.StaticMeshComponent = c end
        a.rotY = 0
        a.K2_SetActorLocationAndRotation = function(self, l, r, sweep, hit, tp)
            assert(type(hit) == "table", "SweepHitResult must be a table")
            self.loc, self.rotY = l, r.Yaw
        end
        a.K2_DestroyActor = function(self) self.destroyed = true; self.IsValid = function() return false end end
    elseif kind == "TextRenderActor" then
        a.TextRender = obj("TextRenderComponent", a._path .. ".TR", {
            SetText = function(self, t) self.text = t end, SetWorldSize = function() end,
            SetHorizontalAlignment = function() end, SetVerticalAlignment = function() end,
            SetTextRenderColor = function() end,
        })
    end
    table.insert(FAKE.spawned, a)
    return a
end
FAKE.newActor = newActor

local classes = {
    ["/Game/Assets/Characters/Blueprints/Biker/Biker_ActorBp.Biker_ActorBp_C"] = obj("Class", "Biker_ActorBp_C", {kind = "Biker_ActorBp_C"}),
    ["/Script/Engine.SkeletalMeshActor"] = obj("Class", "SkeletalMeshActor", {kind = "SkeletalMeshActor"}),
    ["/Script/Engine.TextRenderActor"] = obj("Class", "TextRenderActor", {kind = "TextRenderActor"}),
    ["/Script/Engine.StaticMeshActor"] = obj("Class", "StaticMeshActor", {kind = "StaticMeshActor"}),
    ["/Script/Engine.SkeletalMeshComponent"] = obj("Class", "SkeletalMeshComponent"),
    ["/Script/Engine.StaticMeshComponent"] = obj("Class", "StaticMeshComponent"),
    ["/Script/Engine.Default__KismetSystemLibrary"] = obj("Object", "Kismet", {
        PrintString = function() end,
        ExecuteConsoleCommand = function(self, w, cmd) table.insert(FAKE.console, cmd) end,
    }),
    ["/Script/UMG.Default__WidgetBlueprintLibrary"] = obj("Object", "WBP", {
        SetInputMode_GameOnly = function() end, SetFocusToGameViewport = function() end,
    }),
}
StaticFindObject = function(path)
    if classes[path] or assets[path] then return classes[path] or assets[path] end
    -- Any replicated world mesh: character meshes share the NewBaseMesh skeleton
    if path:find("^/Game/Test/") then asset(path, SK_BASE) return assets[path] end
    return nil
end

-- World entities (customers, cars, trash) living in this instance's world
FAKE.ents = {AICharacterBase = {}, GSSWheeledVehicle = {}, TrashItemBase = {}, PlayerVehicle = {}}
function FAKE.addEntity(class, name, meshes, loc)
    local list = FAKE.ents[class]
    local a = obj(class, "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel." .. name)
    a.loc, a.yaw = {X = loc[1], Y = loc[2], Z = loc[3]}, 0
    a.GetFName = function() return {ToString = function() return name end} end
    local comps = {}
    for i, m in ipairs(meshes) do
        local meshObj = obj("Mesh", m)
        local c = obj("MeshComponent", a._path .. ".C" .. i, {
            IsVisible = function() return true end,
            K2_GetComponentLocation = function() return {X = a.loc.X, Y = a.loc.Y, Z = a.loc.Z} end,
            K2_GetComponentRotation = function() return {Pitch = 0, Yaw = a.yaw, Roll = 0} end,
        })
        if class == "TrashItemBase" then c.StaticMesh = meshObj else c.SkeletalMesh = meshObj end
        comps[i] = c
    end
    if class ~= "TrashItemBase" then a.Mesh = comps[1] end
    a.K2_GetComponentsByClass = function()
        return {ForEach = function(self, fn)
            for i, c in ipairs(comps) do fn(i, {get = function() return c end}) end
        end}
    end
    a.K2_DestroyActor = function(self)
        for i, e in ipairs(list) do if e == self then table.remove(list, i) break end end
        self.IsValid = function() return false end
    end
    table.insert(list, a)
    if class == "PlayerVehicle" then table.insert(FAKE.ents.GSSWheeledVehicle, a) end
    return a
end
FAKE.aiManager = obj("GSSAIManager_BP_C", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.GS.AIManager", {
    MaxVehiclesOnMap = 10, SetComponentTickEnabled = function(self, b) self.ticking = b end,
})
FAKE.spawnPoint = obj("AISpawnPoint", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.SP", {
    SetActorTickEnabled = function(self, b) self.ticking = b end,
})

-- World, controller, player, sky
FAKE.world = obj("World", "/Game/Maps/DemoMapka.DemoMapka", {
    GameState = obj("GSSGameState_BP_C", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.GS",
        {TimeStruct = {Hours = 6, Minutes = 0, Days = 0, TimeOfDay = 600}}),
    SpawnActor = function(self, cls, loc, rot) return newActor(cls.kind, loc) end,
})
FAKE.money = 0
FAKE.pc = obj("GSSPlayerController_BP_C", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.PC", {
    GetMoney = function() return FAKE.money end,
    Cheat_AddMoney = function(self, d) FAKE.money = FAKE.money + d end,
    SetIgnoreLookInput = function() end, SetIgnoreMoveInput = function() end,
})
FAKE.player = obj("PlayerCharacter_BP_C", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.PlayerCharacter_BP_C_0", {
    loc = {X = 0, Y = 0, Z = 100}, Controller = FAKE.pc,
    CapsuleComponent = {GetScaledCapsuleHalfHeight = function() return 88 end},
    K2_GetActorLocation = function(self) return self.loc end,
    K2_GetActorRotation = function() return {Pitch = 0, Yaw = 90, Roll = 0} end,
    GetWorld = function() return FAKE.world end,
})
FAKE.sky = obj("Ultra_Dynamic_Sky_BP_C", "/Game/Maps/DemoMapka.DemoMapka:PersistentLevel.Sky", {["Time of Day"] = 600})

-- Questline: ordered objectives, FinishObjective advances
FAKE.objectives = {}
FAKE.objIndex = 1
FAKE.finishCalls = 0
local function objective(name, countable)
    local o = obj("Objective", "/Engine/Transient.QS:" .. name .. "_" .. math.random(1000), {_classPath = "/Game/Quests/" .. name .. "." .. name .. "_C"})
    o.FinishObjective = function()
        FAKE.finishCalls = FAKE.finishCalls + 1
        FAKE.objIndex = FAKE.objIndex + 1
    end
    if countable then
        o.CurrentProgress = 0
        o.SetObjectiveProgress = function(self, v) self.CurrentProgress = v end
    end
    table.insert(FAKE.objectives, o)
end
objective("Obj_Electricity"); objective("Obj_CleanTrash"); objective("Obj_OpenStation"); objective("Obj_Serve5", true); objective("Obj_Final")
FAKE.questSubsystem = obj("QuestSubsystem", "/Engine/Transient.QuestSubsystem_0", {
    GetFollowedQuestLine = function()
        return obj("ActiveQuestLine", "/Engine/Transient.AQL", {ActiveObjective = FAKE.objectives[FAKE.objIndex]})
    end,
})

-- Main menu (present until the game is entered)
FAKE.menu = obj("MainMenuOverviewWidgetBP_C", "/Game/Menu.Menu:Overview", {
    bCanBeLoaded = true,
    BndEvt__ContinueButton_K2Node_ComponentBoundEvent_1_OnClicked__DelegateSignature = function() FAKE.continueClicked = (FAKE.continueClicked or 0) + 1 end,
    StartNewGame = function() FAKE.newGame = (FAKE.newGame or 0) + 1 end,
})

FindAllOf = function(name)
    if name == "PlayerCharacter_BP_C" then return FAKE.inGame and {FAKE.player} or nil end
    if name == "QuestSubsystem" then return FAKE.inGame and {FAKE.questSubsystem} or nil end
    if name == "MainMenuOverviewWidgetBP_C" then return (not FAKE.inGame) and {FAKE.menu} or nil end
    if name == "World" then return {obj("World", "/Game/Maps/MainMenu.MainMenu"), FAKE.world} end
    if FAKE.ents[name] then
        if not FAKE.inGame or #FAKE.ents[name] == 0 then return nil end
        local copy = {}
        for i, e in ipairs(FAKE.ents[name]) do copy[i] = e end
        return copy
    end
    if name == "AIManager" then return FAKE.inGame and {FAKE.aiManager} or nil end
    if name == "AISpawnPoint" then return FAKE.inGame and {FAKE.spawnPoint} or nil end
    return nil
end
FindFirstOf = function(name)
    if name == "Ultra_Dynamic_Sky_BP_C" then return FAKE.inGame and FAKE.sky or nil end
    local all = FindAllOf(name)
    return all and all[1] or nil
end

function FAKE.tick(ms)
    for _, l in ipairs(FAKE.loops) do
        if ms % l.ms == 0 then l.fn() end
    end
end
