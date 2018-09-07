"""
works in vtk 7; missing surface though
"""
#!/usr/bin/env python

from __future__ import print_function
import math
import vtk

# Available surfaces are:
SURFACE_TYPE = set(["TORUS", "PARAMETRIC_HILLS", "PARAMETRIC_TORUS"])

def WritePNG(ren, fn, magnification = 1):
    """
    Save the image as a PNG
    :param: ren - the renderer.
    :param: fn - the file name.
    :param: magnification - the magnification, usually 1.
    """
    renLgeIm = vtk.vtkRenderLargeImage()
    imgWriter = vtk.vtkPNGWriter()
    renLgeIm.SetInput(ren)
    renLgeIm.SetMagnification(magnification)
    imgWriter.SetInputConnection(renLgeIm.GetOutputPort())
    imgWriter.SetFileName(fn)
    imgWriter.Write()

def MakeBands(dR, numberOfBands, nearestInteger):
    """
    Divide a range into bands
    :param: dR - [min, max] the range that is to be covered by the bands.
    :param: numberOfBands - the number of bands, a positive integer.
    :param: nearestInteger - if True then [floor(min), ceil(max)] is used.
    :return: A List consisting of [min, midpoint, max] for each band.
    """
    bands = list()
    if (dR[1] < dR[0]) or (numberOfBands <= 0):
        return bands
    x = list(dR)
    if nearestInteger:
        x[0] = math.floor(x[0])
        x[1] = math.ceil(x[1])
    dx = (x[1] - x[0])/float(numberOfBands)
    b = [x[0], x[0] + dx / 2.0, x[0] + dx]
    i = 0
    while i < numberOfBands:
        bands.append(b)
        b = [b[0] + dx, b[1] + dx, b[2] + dx]
        i += 1
    return bands

def MakeCustomBands(dR, numberOfBands):
    """
    Divide a range into custom bands.

    You need to specify each band as a list [r1, r2] where r1 < r2 and
    append these to a list (called x in the implementation).
    The list should ultimately look
    like this: x = [[r1, r2], [r2, r3], [r3, r4]...]

    :param: dR - [min, max] the range that is to be covered by the bands.
    :param: numberOfBands - the number of bands, a positive integer.

    :return: A List consisting of [min, midpoint, max] for each band.
    """
    bands = list()
    if (dR[1] < dR[0]) or (numberOfBands <= 0):
        return bands
    x = list()
    x.append([-0.7, -0.05])
    x.append([-0.05, 0])
    x.append([0, 0.13])
    x.append([0.13, 1.07])
    x.append([1.07, 35.4])
    x.append([35.4, 37.1])
    # Set the minimum to match the range minimum.
    x[0][0] = dR[0]
    if len(x) >= numberOfBands:
        x = x[:numberOfBands]
    # Adjust the last band.
    t = (x[len(x) - 1])
    if t[0] > dR[1]:
        t[0] = dR[1]
    t[1] = dR[1]
    x[len(x) - 1] = t
    for e in x:
        bands.append([e[0], e[0] + (e[1] - e[0])/2, e[1]])
    return bands

def Frequencies(bands, src):
    """
    Count the number of scalars in each band.

    :param: bands - the bands.
    :param: src - the vtkPolyData source.

    :return: The frequencies of the scalars in each band.
    """
    freq = dict()
    for i in range(len(bands)):
        freq[i] = 0;
    tuples = src.GetPointData().GetScalars().GetNumberOfTuples()
    for i in range(tuples):
        x = src.GetPointData().GetScalars().GetTuple1(i)
        for j in range(len(bands)):
            if x <= bands[j][2]:
                freq[j] = freq[j] + 1
                break
    return freq

def MakeElevations(src):
    """
    Generate elevations over the surface.

    :param: src - the vtkPolyData source.

    :return: - vtkPolyData source with elevations.
    """
    bounds = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]
    src.GetBounds(bounds)
    elevFilter = vtk.vtkElevationFilter()
    elevFilter.SetInputData(src)
    elevFilter.SetLowPoint(0, bounds[2], 0)
    elevFilter.SetHighPoint(0, bounds[3], 0)
    elevFilter.SetScalarRange(bounds[2], bounds[3])
    elevFilter.Update()
    return elevFilter.GetPolyDataOutput()

def MakeTorus():
    """
    Make a torus as the source.

    :return: vtkPolyData with normal and scalar data.
    """
    source = vtk.vtkSuperquadricSource();
    source.SetCenter(0.0, 0.0, 0.0)
    source.SetScale(1.0, 1.0, 1.0)
    source.SetPhiResolution(64)
    source.SetThetaResolution(64)
    source.SetThetaRoundness(1)
    source.SetThickness(0.5)
    source.SetSize(10)
    source.SetToroidal(1)

    # The quadric is made of strips, so pass it through a triangle filter as
    # the curvature filter only operates on polys
    tri = vtk.vtkTriangleFilter()
    tri.SetInputConnection(source.GetOutputPort())

    # The quadric has nasty discontinuities from the way the edges are generated
    # so let's pass it though a CleanPolyDataFilter and merge any points which
    # are coincident, or very close
    cleaner = vtk.vtkCleanPolyData()
    cleaner.SetInputConnection(tri.GetOutputPort())
    cleaner.SetTolerance(0.005)
    cleaner.Update()
    return CalculateCurvatures(MakeElevations(cleaner.GetOutput()))

def MakeParametricTorus():
    """
    Make a parametric torus as the source.

    :return: vtkPolyData with normal and scalar data.
    """
    fn = vtk.vtkParametricTorus()
    fn.SetRingRadius(5)
    fn.SetCrossSectionRadius(2)

    source = vtk.vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()
    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource)
    source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # We have calculated the elevation, just rename the scalars.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')
    return CalculateCurvatures(source.GetOutput())

def MakeParametricHills():
    """
    Make a parametric hills surface as the source.

    :return: vtkPolyData with normal and scalar data.
    """
    fn = vtk.vtkParametricRandomHills()
    fn.AllowRandomGenerationOn()
    fn.SetRandomSeed(1)
    fn.SetNumberOfHills(30)
    if fn.GetClassName() == 'vtkParametricRandomHills':
        # Make the normals face out of the surface.
        fn.ClockwiseOrderingOff()

    source = vtk.vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()
    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource)
    source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # We have calculated the elevation, just rename the scalars.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')
    return CalculateCurvatures(source.GetOutput())

def Clipper(src, dx, dy, dz):
    """
    Clip a vtkPolyData source.
    A cube is made whose size corresponds the the bounds of the source.
    Then each side is shrunk by the appropriate dx, dy or dz. After
    this operation the source is clipped by the cube.
    :param: src - the vtkPolyData source

    :param: dx - the amount to clip in the x-direction
    :param: dy - the amount to clip in the y-direction
    :param: dz - the amount to clip in the z-direction

    :return: vtkPolyData.
    """
    bounds = [0,0,0,0,0,0]
    src.GetBounds(bounds)

    plane1 = vtk.vtkPlane()
    plane1.SetOrigin(bounds[0] + dx, 0, 0)
    plane1.SetNormal(1, 0, 0)

    plane2 = vtk.vtkPlane()
    plane2.SetOrigin(bounds[1] - dx, 0, 0)
    plane2.SetNormal(-1, 0, 0)

    plane3 = vtk.vtkPlane()
    plane3.SetOrigin(0, bounds[2] + dy, 0)
    plane3.SetNormal(0, 1, 0)

    plane4 = vtk.vtkPlane()
    plane4.SetOrigin(0, bounds[3] - dy, 0)
    plane4.SetNormal(0, -1, 0)

    plane5 = vtk.vtkPlane()
    plane5.SetOrigin(0, 0, bounds[4] + dz)
    plane5.SetNormal(0, 0, 1)

    plane6 = vtk.vtkPlane()
    plane6.SetOrigin(0, 0, bounds[5] - dz)
    plane6.SetNormal(0, 0, -1)

    clipFunction = vtk.vtkImplicitBoolean()
    clipFunction.SetOperationTypeToUnion()
    clipFunction.AddFunction(plane1)
    clipFunction.AddFunction(plane2)
    clipFunction.AddFunction(plane3)
    clipFunction.AddFunction(plane4)
    clipFunction.AddFunction(plane5)
    clipFunction.AddFunction(plane6)

    # Clip it.
    clipper =vtk.vtkClipPolyData()
    clipper.SetClipFunction(clipFunction)
    clipper.SetInputData(src)
    clipper.GenerateClipScalarsOff()
    clipper.GenerateClippedOutputOff()
    #clipper.GenerateClippedOutputOn()
    clipper.Update()
    return clipper.GetOutput()

def CalculateCurvatures(src):
    """
    The source must be triangulated.

    :param: src - the source.

    :return: vtkPolyData with normal and scalar data representing curvatures.
    """
    curvature = vtk.vtkCurvatures()
    curvature.SetCurvatureTypeToGaussian()

    curvature.SetInputData(src)
    curvature.Update()
    return curvature.GetOutput()

def MakeEnneper():
    """
    Make a parametric surface as the source.

    :return: vtkPolyData with normal and scalar data.
    """
    fn = vtk.vtkParametricEnneper()

    source = vtk.vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()
    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource)
    source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # We have calculated the elevation, just rename the scalars.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')
    return CalculateCurvatures(source.GetOutput())

def MakeBoys():
    """
    Make a parametric surface as the source.

    :return: vtkPolyData with normal and scalar data.
    """
    fn = vtk.vtkParametricBoy()

    source = vtk.vtkParametricFunctionSource()
    source.SetParametricFunction(fn)
    source.SetUResolution(50)
    source.SetVResolution(50)
    source.SetScalarModeToZ()
    source.Update()
    # Name the arrays (not needed in VTK 6.2+ for vtkParametricFunctionSource)
    source.GetOutput().GetPointData().GetNormals().SetName('Normals')
    # We have calculated the elevation, just rename the scalars.
    source.GetOutput().GetPointData().GetScalars().SetName('Elevation')
    return CalculateCurvatures(source.GetOutput())

def MakeLUT():
    """
    Make a lookup table using vtkColorSeries.

    :return: An indexed lookup table.
    """
    # Make the lookup table.
    colorSeries = vtk.vtkColorSeries()
    # Select a color scheme.
    #colorSeriesEnum = colorSeries.BREWER_DIVERGING_BROWN_BLUE_GREEN_9
    #colorSeriesEnum = colorSeries.BREWER_DIVERGING_SPECTRAL_10
    #colorSeriesEnum = colorSeries.BREWER_DIVERGING_SPECTRAL_3
    #colorSeriesEnum = colorSeries.BREWER_DIVERGING_PURPLE_ORANGE_9
    #colorSeriesEnum = colorSeries.BREWER_SEQUENTIAL_BLUE_PURPLE_9
    #colorSeriesEnum = colorSeries.BREWER_SEQUENTIAL_BLUE_GREEN_9
    colorSeriesEnum = colorSeries.BREWER_QUALITATIVE_SET3
    #colorSeriesEnum = colorSeries.CITRUS
    colorSeries.SetColorScheme(colorSeriesEnum)
    lut = vtk.vtkLookupTable()
    colorSeries.BuildLookupTable(lut)
    lut.SetNanColor(0,0,0,1)
    return lut

def ReverseLUT(lut):
    """
    Create a lookup table with the colors reversed.

    :param: lut - An indexed lookup table.

    :return: The reversed indexed lookup table.
    """
    lutr = vtk.vtkLookupTable()
    lutr.DeepCopy(lut)
    t = lut.GetNumberOfTableValues() - 1
    revRange = reversed(list(range(t + 1)))
    for i in revRange:
        rgba = [0,0,0]
        v = float(i)
        lut.GetColor(v,rgba)
        rgba.append(lut.GetOpacity(v))
        lutr.SetTableValue(t - i,rgba)
    t = lut.GetNumberOfAnnotatedValues() - 1
    for i in revRange:
        lutr.SetAnnotation(t - i, lut.GetAnnotation(i))
    return lutr

def MakeGlyphs(src, reverseNormals):
    """
    Glyph the normals on the surface.

    You may need to adjust the parameters for maskPts, arrow and glyph for a
    nice appearance.

    :param: src - the surface to glyph.
    :param: reverseNormals - if True the normals on the surface are reversed.

    :return: The glyph object.
    """
    # Sometimes the contouring algorithm can create a volume whose gradient
    # vector and ordering of polygon (using the right hand rule) are
    # inconsistent. vtkReverseSense cures this problem.
    reverse = vtk.vtkReverseSense()

    # Choose a random subset of points.
    maskPts = vtk.vtkMaskPoints()
    maskPts.SetOnRatio(5)
    maskPts.RandomModeOn()
    if reverseNormals:
        reverse.SetInputData(src)
        reverse.ReverseCellsOn()
        reverse.ReverseNormalsOn()
        maskPts.SetInputConnection(reverse.GetOutputPort())
    else:
        maskPts.SetInputData(src)

    # Source for the glyph filter
    arrow = vtk.vtkArrowSource()
    arrow.SetTipResolution(16)
    arrow.SetTipLength(0.3)
    arrow.SetTipRadius(0.1)

    glyph = vtk.vtkGlyph3D()
    glyph.SetSourceConnection(arrow.GetOutputPort())
    glyph.SetInputConnection(maskPts.GetOutputPort())
    glyph.SetVectorModeToUseNormal()
    glyph.SetScaleFactor(1)
    glyph.SetColorModeToColorByVector()
    glyph.SetScaleModeToScaleByVector()
    glyph.OrientOn()
    glyph.Update()
    return glyph

def DisplaySurface(st):
    """
    Make and display the surface.

    :param: st - the surface to display.

    :return The vtkRenderWindowInteractor.
    """
    surface = st.upper()
    if  (not(surface in SURFACE_TYPE) ):
        print(st, "is not a surface.")
        iren = vtk.vtkRenderWindowInteractor()
        return iren
    # ------------------------------------------------------------
    # Create the surface, lookup tables, contour filter etc.
    # ------------------------------------------------------------
    src = vtk.vtkPolyData()
    if surface == "TORUS":
        src = MakeTorus()
    elif surface == "PARAMETRIC_TORUS":
        src = MakeParametricTorus()
    elif surface == "PARAMETRIC_HILLS":
        src = Clipper(MakeParametricHills(),0.5,0.5,0.0)
    else:
        raise RuntimeError(surface)
    # Here we are assuming that the active scalars are the curvatures.
    curvatureName = src.GetPointData().GetScalars().GetName()
    # Use this range to color the glyphs for the normals by elevation.
    src.GetPointData().SetActiveScalars('Elevation')
    scalarRangeElevation = src.GetScalarRange()
    src.GetPointData().SetActiveScalars(curvatureName)
    scalarRangeCurvatures = src.GetScalarRange()
    scalarRange = scalarRangeCurvatures

    lut = MakeLUT()
    numberOfBands = lut.GetNumberOfTableValues()
    bands = MakeBands(scalarRange, numberOfBands, False)
    if surface == "PARAMETRIC_HILLS":
        # Comment this out if you want to see how allocating
        # equally spaced bands works.
        bands = MakeCustomBands(scalarRange, numberOfBands)
        # Adjust the number of table values
        numberOfBands = len(bands)
        lut.SetNumberOfTableValues(numberOfBands)

    lut.SetTableRange(scalarRange)

    # We will use the midpoint of the band as the label.
    labels = []
    for i in range(numberOfBands):
        labels.append('{:4.2f}'.format(bands[i][1]))

    # Annotate
    values = vtk.vtkVariantArray()
    for i in range(len(labels)):
        values.InsertNextValue(vtk.vtkVariant(labels[i]))
    for i in range(values.GetNumberOfTuples()):
        lut.SetAnnotation(i, values.GetValue(i).ToString());

    # Create a lookup table with the colors reversed.
    lutr = ReverseLUT(lut)

    # Create the contour bands.
    bcf = vtk.vtkBandedPolyDataContourFilter()
    bcf.SetInputData(src)
    # Use either the minimum or maximum value for each band.
    for i in range(0, numberOfBands):
        bcf.SetValue(i, bands[i][2])
    # We will use an indexed lookup table.
    bcf.SetScalarModeToIndex()
    bcf.GenerateContourEdgesOn()

    # Generate the glyphs on the original surface.
    glyph = MakeGlyphs(src,False)

    # ------------------------------------------------------------
    # Create the mappers and actors
    # ------------------------------------------------------------
    srcMapper = vtk.vtkPolyDataMapper()
    srcMapper.SetInputConnection(bcf.GetOutputPort())
    srcMapper.SetScalarRange(scalarRange)
    srcMapper.SetLookupTable(lut)
    srcMapper.SetScalarModeToUseCellData()

    srcActor = vtk.vtkActor()
    srcActor.SetMapper(srcMapper)
    srcActor.RotateX(-45)
    srcActor.RotateZ(45)

    # Create contour edges
    edgeMapper = vtk.vtkPolyDataMapper()
    edgeMapper.SetInputData(bcf.GetContourEdgesOutput())
    edgeMapper.SetResolveCoincidentTopologyToPolygonOffset()

    edgeActor = vtk.vtkActor()
    edgeActor.SetMapper(edgeMapper)
    edgeActor.GetProperty().SetColor(0, 0, 0)
    edgeActor.RotateX(-45)
    edgeActor.RotateZ(45)

    glyphMapper = vtk.vtkPolyDataMapper()
    glyphMapper.SetInputConnection(glyph.GetOutputPort())
    glyphMapper.SetScalarModeToUsePointFieldData()
    glyphMapper.SetColorModeToMapScalars()
    glyphMapper.ScalarVisibilityOn()
    glyphMapper.SelectColorArray('Elevation')
    # Colour by scalars.
    glyphMapper.SetScalarRange(scalarRangeElevation)

    glyphActor = vtk.vtkActor()
    glyphActor.SetMapper(glyphMapper)
    glyphActor.RotateX(-45)
    glyphActor.RotateZ(45)

    # Add a scalar bar.
    scalarBar = vtk.vtkScalarBarActor()
    # This LUT puts the lowest value at the top of the scalar bar.
    # scalarBar->SetLookupTable(lut);
    # Use this LUT if you want the highest value at the top.
    scalarBar.SetLookupTable(lutr)
    scalarBar.SetTitle('Gaussian\nCurvature')

    # ------------------------------------------------------------
    # Create the RenderWindow, Renderer and Interactor
    # ------------------------------------------------------------
    ren = vtk.vtkRenderer()
    renWin = vtk.vtkRenderWindow()
    iren = vtk.vtkRenderWindowInteractor()

    renWin.AddRenderer(ren)
    iren.SetRenderWindow(renWin)

    # add actors
    ren.AddViewProp(srcActor)
    ren.AddViewProp(edgeActor)
    ren.AddViewProp(glyphActor)
    ren.AddActor2D(scalarBar)

    ren.SetBackground(0.7, 0.8, 1.0)
    renWin.SetSize(800, 800)
    renWin.Render()

    ren.GetActiveCamera().Zoom(1.5)

    return iren

if __name__ == '__main__':
    #iren = vtk.vtkRenderWindowInteractor()
    #iren = DisplaySurface("TORUS")
    #iren = DisplaySurface("PARAMETRIC_TORUS")
    iren = DisplaySurface("PARAMETRIC_HILLS")
    iren.Render()
    iren.Start()
#     WritePNG(iren.GetRenderWindow().GetRenderers().GetFirstRenderer(),
#               "CurvatureBandsWithGlyphs.png")