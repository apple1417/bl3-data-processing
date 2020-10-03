import bl3dump

missions = bl3dump.AssetFolder("/Game/Missions/")

unknown = set()
repeatable = set()

for asset in missions.search_child_files(prefix="Mission_"):
    try:
        obj = next(asset.iter_exports_of_class("BlueprintGeneratedClass"))["_jwp_object_name"]
        data = next(asset.iter_exports_of_class(obj))
        if "bRepeatable" in data and data["bRepeatable"]:
            name = data["FormattedMissionName"]["FormatText"]["string"]
            repeatable.add(name)
    except RuntimeError:
        unknown.add(asset)
        continue

print("Repeatables:")
for i in repeatable:
    print(i)

print()
print("Unknown:")
for i in unknown:
    print(i)
