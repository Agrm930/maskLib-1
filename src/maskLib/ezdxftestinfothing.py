# Edited by Agrim, 2026 (fixed removed ezdxf import)
import ezdxf
from ezdxf.addons import text2path
# NOTE: ezdxf reorganized its font tools in v1.0 and later removed the old path:
#   old (removed):  from ezdxf.tools.fonts import FontFace
#   new:            from ezdxf.fonts.fonts import FontFace
from ezdxf.fonts.fonts import FontFace

# Define the text and font
text = "p"
font_face = FontFace(family='Arial')

# Convert text to paths
paths = text2path.make_paths_from_str(text, font=font_face, size=10)

# Get the starting point of the first path (which should be the "p")
start_point = paths[0].start

print(f"Starting point of 'p': {start_point}")

# Create a new DXF document
doc = ezdxf.new('R2010')
msp = doc.modelspace()

# Create a block for the text
# NOTE: this document is an ezdxf document, so the block must be created with
# the ezdxf API (doc.blocks.new). The original code built a dxfwrite block
# (dxf.block) and tried to add it here -- the two libraries' objects are not
# interchangeable.
block_name = "TEXT_BLOCK"
text_block = doc.blocks.new(name=block_name)

# Add the text paths to the block as closed polylines
for path in paths:
    points = [(p.x, p.y) for p in path.flattening(0.01)]
    text_block.add_lwpolyline(points, close=True, dxfattribs={'layer': 'TEXT'})

# Add the block reference to the modelspace
msp.add_blockref(block_name, insert=(0, 0))

# Add a circle at the starting point for easy identification
msp.add_circle(center=(start_point.x, start_point.y), radius=0.1, dxfattribs={'color': 1})

# Save the DXF document
doc.saveas('text_with_start_point.dxf')
print("DXF file created: text_with_start_point.dxf")