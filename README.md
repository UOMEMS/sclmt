## Background

This package generates fracture-free laser machining sequences for prestressed membranes at the micro/nano scale. It has successfully been used to fabricate nanoresonators from square silicon nitride membranes with a nominal thickness of 100 nm and a built-in stress of 100 MPa.

The underlying sequencing algorithm lays a staggered pattern of holes in successive passes, allowing layouts to be machined from membranes without forming cracks (adapted from [Xie et. al](https://doi.org/10.1016/j.jmatprotec.2023.118001)).

<figure>
  <img src="assets\machining_sequence_demo.gif" width="600"/>
  <figcaption>Trampoline machining sequence (each color represents a different pass and holes are not to scale).</figcaption>
</figure>

## Usage

The `LayoutSequencer` class generates laser machining sequences for entire layouts. It includes methods for loading the layout, performing layout transformations, configuring machining parameters, previewing the sequence, and handling file I/O.

For basic use, layouts can be provided as a list of polygons represented by their vertices and sequenced as follows. *Note that all configurations are optional and will default to the values specified in the* `memslasermachining.config` *file if omitted.*

```python
from memslasermachining import LayoutSequencer

# Vertices of polygons to be machined
square = [
    [1, 1],
    [1, 6],
    [6, 6],
    [6, 1]
]
triangle = [
    [-1, -1],
    [-1, -6],
    [-6, -6]
]

# Configure sequencer
sequencer = LayoutSequencer()
(sequencer
    # Set length unit to microns for layout and configurations
    .set_length_unit(1e-6)
    # Merge the laser machining passes of all polygons
    .set_staggered(True)
    # Load the layout (list of polygons) to be laser machined
    .set_polygons([square, triangle])
    # Set the targeted initial pass separation between adjacent 
    # hole centers for each polygon
    .set_target_separation([2, 4], init_pass = True)
    # Set the targeted final pass separation between adjacent 
    # hole centers for each polygon
    .set_target_separation([0.5, 1], init_pass = False)
    # Scale layout by factor of 2 and rotate by 180 degrees
    .scale_layout(2)
    .rotate_layout(3.14)
    # Generate and preview the machining sequence 
    .generate_sequence()
    .view_sequence()
)
```

More commonly, layouts are provided as GDSII files, and their sequences are written to some type of numerical control (e.g., G-code) file. This package offers two file interfaces (abstract classes), `FileReader` and `FileWriter`, for this purpose. Concrete implementations of these interfaces can be passed to `LayoutSequencer`. Two such implementations are provided by default: `GDSFileReader` and `AeroBasicFileWriter` (used to generate PGM files for an Aerotech A3200 controller).

To successfully machine a layout from a GDSII file, the file must meet the requirements outlined in the following section. The example below demonstrates the use of file interfaces and a special compensation method, which is discussed in more detail in a later section.

```python
from memslasermachining import (
    GDSFileReader,
    AeroBasicFileWriter,
    LayoutSequencer
)

# Instantiate file reader and preview GDS layout
file_reader = GDSFileReader('layout.gds')
file_reader.view_layout()

# Instantiate file writer and set laser and stage parameters
file_writer = AeroBasicFileWriter('laser_machining_sequence.pgm')
file_writer.set_stage_params(coordinated_motion_transition_feedrate = 5,
                             shape_feedrate = 2)
file_writer.set_laser_params(pulse_num = 5, 
                             frequency_Hz = 100000)

sequencer = LayoutSequencer()
(sequencer
    # Pass file reader
    .read_file(file_reader)
    # Compensate for misalignment and variance between the 
    # nominal and actual size of the square membrane being machined
    .compensate(nominal_membrane_side_length = 1, 
                disp_x = 1.12763114494, 
                disp_y = 0.410424171991)
    .generate_sequence()
    # Pass file writer
    .write_file(file_writer)
)
```

```
Output:
Acutal membrane side length: 1.2.
Layout scaled by 20.0% and rotated by 20 degrees.
Vector from bottom right corner to membrane center:
x -> -0.7690276584655001, y -> 0.3586034864745.
```

## GDSII File Requirements & Guidelines

- Files must be composed of a single cell with no references
- If the layout is to be subsequently scaled or rotated, it must be centered on the origin (0,0)
- Each geometric entity to be machined must have its `layer` property set to 0 (the default) and its `datatype` property set to its order in the global machining sequence; each polygon must have a unique `datatype`
    - Note that `layer` and `datatype` properties have no predefined meaning
    - For `gdspy` classes that generate multiple polygons (e.g., `gdspy.Text`), edit the `obj.datatypes` attribute (list) after construction
- Contact between polygons should be avoided since this causes unnecessary machining of shared edges; a single equivalent polygon should be used instead
    - To avoid fracturing (i.e., decomposing into sub-polygons) filleted polygons, polygonal approximations of circles/ellipses, and curved paths in `gdspy`, set the `max_points` argument in the respective method or constructor to a large number
    - To avoid fractured paths, use `gdspy.FlexPath`

## Compensation

The `compensate()` method in `LayoutSequencer` scales and rotates the loaded layout to address variances between the nominal and actual size of the square membrane being machined, as well as any misalignment with the laser machining stage. This method is essential whenever features need to be machined on the membrane boundary. If measurement accuracy is limited, add a 1-micron padding to the displacement values, resulting in the layout being slightly inset.

<figure>
  <img src="assets\compensation_diagram.jpg" width="600"/>
  <figcaption>Membrane compensation diagram.</figcaption>
</figure>

**Symbols:**

- $L$: actual membrane side length
- $\Delta x, \Delta y$: displacement from bottom left to bottom right corner
    - $\theta_{m}$: membrane angle
- $\vec{v}$: vector from bottom right corner to the membrane center
    - $\theta_{v}$: angle of $\vec{v}$

**Cases:**

1. $\Delta x, \Delta y > 0, \theta_{m} > 0$
2. $\theta_{m}=\pm45$°, depending on which corners are chosen
3. $\Delta x > 0, \Delta y < 0, \theta_{m} < 0$

**Properties:**

- $-45°≤\theta_{m}≤45°$ or else the wrong corners were chosen
- If not zero, $v_x$ is always negative, and $v_y$ is always positive