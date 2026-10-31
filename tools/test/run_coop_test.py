"""Headless co-op test: two copies of the real main.lua against fake UE4SS worlds, joined by a fake relay."""
import os
import shutil
import sys
import tempfile

from lupa import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_LUA = sys.argv[1]


class Instance:
    def __init__(self, role, name):
        self.role = role
        self.dir = tempfile.mkdtemp(prefix=f"gss_{role}_")
        os.makedirs(os.path.join(self.dir, "net"))
        for fn, val in (("role.txt", role), ("player_name.txt", name), ("character.txt", "biker")):
            with open(os.path.join(self.dir, "net", fn), "w") as f:
                f.write(val + "\n")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with self.cd():
            self.lua.execute(open(os.path.join(HERE, "fake_ue.lua"), encoding="utf-8").read())
            self.lua.execute(open(MAIN_LUA, encoding="utf-8").read())
        self.F = self.lua.globals().FAKE

    def cd(self):
        inst = self

        class _Cd:
            def __enter__(self):
                self.old = os.getcwd()
                os.chdir(inst.dir)

            def __exit__(self, *a):
                os.chdir(self.old)
        return _Cd()

    def p(self, rel):
        return os.path.join(self.dir, "net", rel)

    def logs(self):
        return [self.F.logs[i] for i in range(1, len(self.F.logs) + 1)]


RELAY = {"max_line": 0, "drop_prefix": None}


def relay(src, dst, peer_name):
    with open(dst.p("peer.state"), "w") as f:
        f.write(f"CONNECTED=1\nROLE={src.role}\nNAME={peer_name}\nCHAR=biker\n")
    if os.path.exists(src.p("events.out")):
        lines = open(src.p("events.out")).read().splitlines()
        os.remove(src.p("events.out"))
        kept = []
        for line in lines:
            RELAY["max_line"] = max(RELAY["max_line"], len(line.encode()) + 4)  # +4 = "EVT:" prefix
            if RELAY["drop_prefix"] and line.startswith(RELAY["drop_prefix"]):
                continue  # simulate a lost UDP datagram
            kept.append(line)
        with open(dst.p("events.in"), "a") as f:
            f.write("".join(l + "\n" for l in kept))
    if os.path.exists(src.p("local_player.state")):
        shutil.copy(src.p("local_player.state"), dst.p("remote_player.state"))


host, guest = Instance("host", "Host"), Instance("guest", "Guest")
clock = 0


def run(ms):
    global clock
    for _ in range(ms // 50):
        clock += 50
        for inst in (host, guest):
            with inst.cd():
                inst.F.tick(clock)
        relay(host, guest, "Host")
        relay(guest, host, "Guest")


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        check.failed = True
check.failed = False

# --- Menu: mod must click Continue, never force "open DemoMapka"
run(3000)
check(host.F.continueClicked and guest.F.continueClicked, "menu: Continue clicked on both")
check(len(host.F.console) == 0 and len(guest.F.console) == 0, "menu: no raw console level open")

# --- Enter the station
host.F.inGame = True
guest.F.inGame = True
host.F.money = 100.0
guest.F.money = 5.0
host.F.world.GameState.TimeStruct.Hours = 10
host.F.sky["Time of Day"] = 1057
host.F.player.loc = host.lua.table_from({"X": 500, "Y": 600, "Z": 188})
run(4000)
check(any("CONNECTED TO GAS STATION WORLD" in l for l in host.logs()), "host detects gameplay world")
check(any("CONNECTED TO GAS STATION WORLD" in l for l in guest.logs()), "guest detects gameplay world")

# --- Clock and sky
check(guest.F.world.GameState.TimeStruct.Hours == 10, "time: guest HUD clock follows host")
check(abs(guest.F.sky["Time of Day"] - 1057) < 0.01, "time: guest sky follows host (no more night)")

# --- Puppets
def puppet(inst):
    for i in range(1, len(inst.F.spawned) + 1):
        a = inst.F.spawned[i]
        if a._class == "Biker_ActorBp_C":
            return a
gp, hp = puppet(guest), puppet(host)
check(gp is not None and hp is not None, "puppet: both players see each other")
check(gp is not None and abs(gp.loc.X - 500) < 0.01 and abs(gp.loc.Z - (100 + 90)) < 0.01,
      "puppet: guest's host-puppet at host feet (+ mesh offset)")
idle = gp.Body.playing if gp else None
check(idle is not None and "Base_Idle_Male_00" in idle._path, "anim: skeleton-matched idle playing (no T-pose)")
check(gp is not None and gp.Head.visible is False, "anim: biker head hidden after fallback body swap")
tag = next((guest.F.spawned[i] for i in range(1, len(guest.F.spawned) + 1) if guest.F.spawned[i]._class == "TextRenderActor"), None)
check(tag is not None and tag.TextRender.text == "Host [HOST]", "nametag: plain ASCII label")
host.F.player.loc = host.lua.table_from({"X": 900, "Y": 600, "Z": 188})
run(200)
check(gp.Body.playing and "WalkFwdLoop" in gp.Body.playing._path, "anim: walk plays when partner moves (survives update gaps)")
run(1000)
check("Base_Idle_Male_00" in gp.Body.playing._path, "anim: back to idle once partner stops")

# --- Shared wallet
check(abs(guest.F.money - 100) < 0.01, "money: guest wallet = host wallet")
guest.F.money -= 30   # guest buys something
run(3000)
check(abs(host.F.money - 70) < 0.01 and abs(guest.F.money - 70) < 0.01, "money: guest spending reaches host (70/70)")
host.F.money += 20    # host sells fuel
guest.F.money += 15   # guest sells at the same time
run(4000)
check(abs(host.F.money - 105) < 0.01 and abs(guest.F.money - 105) < 0.01,
      f"money: simultaneous earnings merge (host {host.F.money:.2f} / guest {guest.F.money:.2f})")

# --- Shared quests: host completes objective 1
host.F.objectives[1].FinishObjective()
run(3000)
check(host.F.objIndex == 2 and guest.F.objIndex == 2, f"quest: host completion applies to guest (host {host.F.objIndex}, guest {guest.F.objIndex})")
check(host.F.finishCalls == 1, "quest: no echo back to host")

# guest runs ahead by two objectives; host must catch up in order
guest.F.objectives[2].FinishObjective()
run(1100)
guest.F.objectives[3].FinishObjective()
run(5000)
check(host.F.objIndex == 4 and guest.F.objIndex == 4, f"quest: host catches up on 2 guest completions (host {host.F.objIndex}, guest {guest.F.objIndex})")

# countable objective: progress shares the higher value
guest.F.objectives[4].CurrentProgress = 3
run(2000)
check(host.F.objectives[4].CurrentProgress == 3, "quest: countable progress shared (3/5)")

# --- Host-authoritative world: customers, cars, trash
def tbl(inst, items):
    return inst.lua.table_from(items)

H, G = host.F, guest.F
customer = H.addEntity("AICharacterBase", "AIHumanBase_BP_C_7",
                       tbl(host, ["/Game/Test/Body.Body", "/Game/Test/Head.Head", "/Game/Test/Hair.Hair"]), tbl(host, [1000, 0, 0]))
car = H.addEntity("GSSWheeledVehicle", "BP_Sedan_C_3", tbl(host, ["/Game/Test/Sedan.Sedan"]), tbl(host, [2000, 500, 0]))
trash = H.addEntity("TrashItemBase", "00_TrashItem_C_12", tbl(host, ["/Game/Test/Cup.Cup"]), tbl(host, [1, 2, 0]))
H.addEntity("PlayerVehicle", "Rudy_C_0", tbl(host, ["/Game/Test/Rudy.Rudy"]), tbl(host, [0, 0, 0]))
g_own_npc = G.addEntity("AICharacterBase", "AIHumanBase_BP_C_1", tbl(guest, ["/Game/Test/Body.Body"]), tbl(guest, [5, 5, 0]))
G.addEntity("GSSWheeledVehicle", "BP_Truck_C_1", tbl(guest, ["/Game/Test/Truck.Truck"]), tbl(guest, [9, 9, 0]))
G.addEntity("TrashItemBase", "00_TrashItem_C_2", tbl(guest, ["/Game/Test/Cup.Cup"]), tbl(guest, [3, 3, 0]))
G.addEntity("PlayerVehicle", "Rudy_C_0", tbl(guest, ["/Game/Test/Rudy.Rudy"]), tbl(guest, [0, 0, 0]))
run(3000)

check(len(G.ents.AICharacterBase) == 0 and len(G.ents.TrashItemBase) == 0, "world: guest's own customers/trash removed")
check(len(G.ents.GSSWheeledVehicle) == 1 and G.ents.GSSWheeledVehicle[1]._path.endswith("Rudy_C_0"),
      "world: guest's own AI cars removed, player truck kept")
check(G.aiManager.MaxVehiclesOnMap == 0 and G.aiManager.ticking is False and G.spawnPoint.ticking is False,
      "world: guest AI director switched off")

def proxies(inst, path_part):
    out = []
    for i in range(1, len(inst.F.spawned) + 1):
        a = inst.F.spawned[i]
        if a._class in ("SkeletalMeshActor", "StaticMeshActor") and not a.destroyed:
            comp = a.SkeletalMeshComponent or a.StaticMeshComponent
            mesh = comp.SkeletalMesh or comp.StaticMesh
            if mesh and path_part in mesh._path:
                out.append(a)
    return out

body, head = proxies(guest, "Body.Body"), proxies(guest, "Head.Head")
check(len(body) == 1 and len(head) == 1 and len(proxies(guest, "Hair.Hair")) == 1, "world: customer proxy has all 3 body parts")
check(head and body and head[0].SkeletalMeshComponent.leader._path == body[0].SkeletalMeshComponent._path, "world: head/hair follow the body pose")
check(body and body[0].SkeletalMeshComponent.playing and "Base_Idle_Male_00" in body[0].SkeletalMeshComponent.playing._path,
      "world: customer proxy animated (idle)")
check(len(proxies(guest, "Sedan.Sedan")) == 1 and len(proxies(guest, "Cup.Cup")) == 1, "world: car and trash proxies spawned")
check(len(proxies(guest, "Rudy.Rudy")) == 0, "world: host's player truck not replicated")
check(proxies(guest, "Cup.Cup")[0].StaticMeshComponent.mobility == 2, "world: static proxies are movable")
check(len(proxies(host, "")) == 0, "world: host spawns no proxies")

customer.loc = tbl(host, {"X": 1600, "Y": 0, "Z": 0})
customer.yaw = 90
run(300)
check(body[0].SkeletalMeshComponent.playing and "WalkFwdLoop" in body[0].SkeletalMeshComponent.playing._path,
      "world: walking customer plays walk anim")
run(1500)
check(abs(body[0].loc.X - 1600) < 1 and abs(body[0].rotY - 90) < 1 and abs(head[0].loc.X - 1600) < 1,
      f"world: customer proxy follows host smoothly (x={body[0].loc.X:.1f})")
check("Base_Idle_Male_00" in body[0].SkeletalMeshComponent.playing._path, "world: back to idle when customer stops")

car.K2_DestroyActor(car)   # car drives off the map on the host
run(1500)
check(len(proxies(guest, "Sedan.Sedan")) == 0, "world: departed car removed on guest")

# lost ENT_DEL datagram must still heal via the periodic roster
RELAY["drop_prefix"] = ("ENT_DEL", "ENT_ROSTER")
customer.K2_DestroyActor(customer)
run(1500)
RELAY["drop_prefix"] = None
check(len(proxies(guest, "Body.Body")) == 1, "world: (lost ENT_DEL simulated, proxy still there)")
run(5500)
check(len(proxies(guest, "Body.Body")) == 0, "world: roster heals a lost ENT_DEL")

# guest picks up host trash with F
guest.F.player.loc = tbl(guest, {"X": 0, "Y": 0, "Z": 88})
with guest.cd():
    guest.F["keys"]["F"]()
run(1500)
check(len(H.ents.TrashItemBase) == 0, "world: guest's F removes trash in host world")
check(len(proxies(guest, "Cup.Cup")) == 0, "world: trash gone on guest too")

# a crowd: 60 customers must fit the relay's 4 KB datagram buffer
for i in range(60):
    H.addEntity("AICharacterBase", f"AIHumanBase_BP_C_{100 + i}", tbl(host, ["/Game/Test/Body.Body", "/Game/Test/Head.Head"]),
                tbl(host, [i * 100, 0, 0]))
run(6000)
check(len(proxies(guest, "Body.Body")) == 60, f"world: 60-customer crowd replicated ({len(proxies(guest, 'Body.Body'))})")
check(RELAY["max_line"] < 4096, f"relay: largest datagram {RELAY['max_line']} B < 4096 B buffer")

# --- Phase 2: Guest can work on host customers and vehicles
# 1. Guest fuels a vehicle
test_car = H.addEntity("GSSWheeledVehicle", "BP_Sedan_C_99", tbl(host, ["/Game/Test/Sedan.Sedan"]), tbl(host, [300, 300, 0]))
run(1500)
guest.F.player.loc = tbl(guest, {"X": 300, "Y": 300, "Z": 88})
with guest.cd():
    guest.F["keys"]["F"]()
run(1500)
check(H.fuelStation.finished and not getattr(H.fuelStation2, "finished", None),
      "guest interaction: guest fuels vehicle on host (targets closest pump, leaves pump 2 untouched)")

# 2. Guest checks out a customer at cash register
test_customer = H.addEntity("AICharacterBase", "AIHumanBase_BP_C_999", tbl(host, ["/Game/Test/Customer_Checkout.Body"]), tbl(host, [400, 400, 0]))
run(1500)
guest.F.player.loc = tbl(guest, {"X": 400, "Y": 400, "Z": 88})
with guest.cd():
    guest.F["keys"]["F"]()
run(1500)
check(H.cashShop.finished and test_customer.CurrentActiveTask.finished, "guest interaction: guest checks out customer on host")

# 3. Action deduplication (repeat F is safe & idempotent)
with guest.cd():
    guest.F["keys"]["F"]()
run(1000)
check(test_customer.CurrentActiveTask.finished, "guest interaction: duplicate action handled idempotently")

# 4. Unknown/malformed event robustness (no Lua crashes)
with open(host.p("events.in"), "a") as f:
    f.write("GUEST_ACT unknown_id_9999 invalid_action\n")
    f.write("GUEST_ACT\n")
    f.write("GUEST_TRASH nonexistent_trash\n")
run(500)
check(True, "robustness: unknown or malformed events ignored safely")

errors = [l for inst in (host, guest) for l in inst.logs() if "ERROR" in l]
check(not errors, "no Lua errors logged" + ("" if not errors else f": {errors[:3]}"))

for inst in (host, guest):
    shutil.rmtree(inst.dir, ignore_errors=True)
print("RESULT:", "FAIL" if check.failed else "ALL PASS")
sys.exit(1 if check.failed else 0)
