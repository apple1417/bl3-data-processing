from bl3dump import DATA_PATH

print(
    max(
        (
            (p := str(path), len(p))
            for path in DATA_PATH.glob("**/*.*")
        ),
        key=lambda x: x[1]
    )[0]
)
