# Claude Code Companion Feedback & Peer Review

## Analysis Date: 2026-10-29

### Key Insights & Findings:
1. **Network Handshake & Connection Verification**:
   - Previously, `main.lua` showed connected merely when the local map `DemoMapka` was loaded, without checking whether UDP packets had arrived from the peer.
   - Implemented bidirectional handshake: Guest sends `HELLO:<name>:<char_id>`, Host replies `WELCOME:<name>:<char_id>`. Both write `net/peer.state`.
   - In-game HUD now only indicates `CONNECTED` when `peer.state` was verified within the last 3 seconds.

2. **Visible 3D Character Puppets**:
   - In GSS (UE 4.27 first-person game), the local player pawn mesh is only `Player_Hands_SK` (floating hands) and `ShadowCaster_SK`.
   - `summon SkeletalMeshActor` console command is disabled in shipping builds and grabbed random props from the map.
   - Spawning is now done via native engine spawner `World:SpawnActor` / `UGameplayStatics::BeginSpawningActorFromClass` with full character meshes:
     - `biker`: `/Game/Assets/Characters/Biker/biker_body_SK.biker_body_SK` (or `Biker_ActorBp_C`)
     - `delivery`: `/Game/Assets/Characters/NewBaseMesh/DeliveryGuys/SK_Ma_GasolineDelivery_T.SK_Ma_GasolineDelivery_T`
     - `worker`: `/Game/Assets/Characters/PlayerModularSkeleton/Player_Modular_Base_01.Player_Modular_Base_01`
     - `party`: `/Game/Assets/Characters/NewBaseMesh/Party/SK_Ma_BusParty_10.SK_Ma_BusParty_10`

3. **In-World 3D Floating Name Tags**:
   - Spawned `ATextRenderActor` (`/Script/Engine.TextRenderActor`) positioned at `Z + 115` above puppet.
   - Dynamic billboard Yaw rotation towards local camera.

4. **Crash Prevention (`0xe06d7363` C++ MSVC Exception)**:
   - Fixed `K2_SetActorLocationAndRotation`: Replaced `nil` SweepHitResult parameter with empty table `{}`.
   - Debounced level loading transitions to prevent race conditions.
   - Removed blocking `/wait` flag from `start "" pythonw ...`.

5. **Launcher UI Optimization (No Freeze / Not Responding)**:
   - Moved network IP resolution and UDP discovery to background daemon threads with instant cache.
   - Interactive 4-archetype character picker card grid.
