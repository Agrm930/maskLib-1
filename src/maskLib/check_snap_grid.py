import sys
import math

def is_on_grid(x, y, grid_size, eps=1e-6):
    # Check if x and y are within eps of a grid point
    return (abs((x % grid_size)) < eps or abs((x % grid_size) - grid_size) < eps) and \
           (abs((y % grid_size)) < eps or abs((y % grid_size) - grid_size) < eps)

def check_points_on_grid(points_file, grid_size=50):
    off_grid_points = []
    total_points = 0
    with open(points_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                x_str, y_str = line.split(',')
                x, y = float(x_str), float(y_str)
                total_points += 1
                if not is_on_grid(x, y, grid_size):
                    off_grid_points.append((line_num, x, y))
            except Exception:
                print(f"Skipping invalid line {line_num}: {line}")
    return off_grid_points, total_points

if __name__ == "__main__":
    points_file = r'S:\_People\Tom DiNapoli\maskLib\Localonly\points_list.txt'
    grid_size = .05
    if len(sys.argv) > 1:
        points_file = sys.argv[1]
    if len(sys.argv) > 2:
        grid_size = float(sys.argv[2])
    off_grid, total_points = check_points_on_grid(points_file, grid_size)
    if off_grid:
        print(f"Points not on {grid_size}um snap grid:")
        for line_num, x, y in off_grid:
            print(f"Line {line_num}: ({x}, {y})")
        print(f"Total off-grid points: {len(off_grid)}")
    else:
        print("All points are on the snap grid.")
    print(f"Total points checked: {total_points}")
