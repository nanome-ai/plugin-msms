

from nanome.util import Logs, Process

class MSMSProcess():
    def __init__(self, plugin):
    	self.__plugin = plugin
		self.__process_running = False

    def start_process(self, workspace):
		#Run MSMS on every complex
        for c in workspace.complexes:
            positions = []
            radii = []
            molecule = c._molecules[c.current_frame]
            for atom in molecule.atoms:
                positions.append(atom.position)
                radii.append(atom.radius)
            
            msms_input = tempfile.NamedTemporaryFile(delete=False, suffix='.xyzr')
            msms_output = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
            with open(msms_input.name, 'w') as msms_file:
                for i in range(len(positions)):
                    msms_file.write("{0:.5f} {1:.5f} {2:.5f} {3:.5f}\n".format(positions[i].x, positions[i].y, positions[i].z, radii[i]))
            exePath = getMSMSExecutable()
            probeRadius = "1.4"
            density = "1.0"
            hdensity = "3.0"

            subprocess.run([exePath, "-if ", msms_input.name, "-of ", msms_output.name, "-probe_radius", probeRadius, "-density", density, "-hdensity", hdensity, "-no_area", "-no_rest", "-no_header"])
            if os.path.isfile(msms_output + ".vert") and os.path.isfile(msms_output + ".face"):
                verts, norms, indices = parseVerticesNormals(msms_output + ".vert")
                faces = parseFaces(msms_output + ".face")

                make_mesh(verts, norms, tris)

            else:
                Logs.error("Failed to run MSMS")
        stop_process()
	
	def stop_process(self):
	    if self.__process_running:
	    	self.__process.stop()
	    self.__process_running = False

    def update(self):
        if not self.__process_running:
            Logs.debug('MSMS done')
            self.stop_process()

    def __on_process_error(self, error):
        Logs.warning('Error during MSMS:')
        Logs.warning(error)

def make_mesh(v, n, t):
    #Create nanome shape
    mesh = shapes.Mesh()
    mesh.uv = []
    mesh.vertices = np.asarray(v).flatten()
    mesh.normals = np.asarray(n).flatten()
    mesh.triangles = np.asarray(t).flatten()
    mesh.colors = []
    mesh.anchors[0].anchor_type = nanome.util.enums.ShapeAnchorType.Complex
    mesh.anchors[0].position = nanome.util.Vector3(0, 0, 0)
    mesh.color = nanome.util.Color(255, 255, 255, 255)
    mesh.upload()

def getMSMSExecutable():
    if platform == "linux" or platform == "linux2":
        return "MSMS_binaries/Linux/msms"
    elif platform == "darwin":
        return "MSMS_binaries/OSX/msms"
    elif platform == "win32":
        return "MSMS_binaries/Windows/msms.exe"

def parseVerticesNormals(path):
    verts = []
    norms = []
    indices = []
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            if l.startswith("#"):
                continue
            s = l.split()
            v = [float(s[0]), float(s[1]), float(s[2])]
            n = [float(s[3]), float(s[4]), float(s[5])]
            idx = int(s[7] - 1)
            verts += v
            norms += n
            indices += idx
    return (verts, norms, indices)

def parseFaces(path):
    tris = []
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            if l.startswith("#"):
                continue
            s = l.split()
            t = [int(s[0]) - 1, int(s[1]) - 1, int(s[2]) - 1]
            tris += t
    return tris