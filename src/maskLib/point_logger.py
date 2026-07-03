points = []

def log_point(pt):
    points.append(tuple(pt))

def log_points(pts):
    for pt in pts:
        log_point(pt)

def write_points(filename="points_list.txt"):
    with open(filename, "w") as f:
        for pt in points:
            f.write(f"{pt[0]}, {pt[1]}\n")
