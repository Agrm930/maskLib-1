def is_off_grid(x, y, min_x=0, max_x=100, min_y=0, max_y=100):
    return not (min_x <= x <= max_x and min_y <= y <= max_y)

def check_points_off_grid(points_file):
    off_grid_points = []
    with open(points_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                x_str, y_str = line.split(',')
                x, y = float(x_str), float(y_str)
                if is_off_grid(x, y):
                    off_grid_points.append((line_num, x, y))
            except Exception as e:
                print(f"Skipping invalid line {line_num}: {line}")
    return off_grid_points

if __name__ == "__main__":
    points_file = r'S:\_People\Tom DiNapoli\maskLib\Localonly\points_list.txt'
    off_grid = check_points_off_grid(points_file)
    if off_grid:
        print("Off-grid points found:")
        for line_num, x, y in off_grid:
            print(f"Line {line_num}: ({x}, {y})")
    else:
        print("No off-grid points found.")
