from fenics import *
from dolfin import *
from mshr import *
from vtkplotter.dolfin import plot, datadir, Latex
import numpy as np
import my_functions as mf
import mshr
import math 




mesh = Mesh()
# Create list of polygonal domain vertices
channel_file=mf.import_file('/home/matteo/Desktop/Python_Code/FEniCS_Simulations/Rheoflu_simulations/Channel_shape','.txt');
c=np.loadtxt(channel_file[0]);
a=c[-3080:-2700:10]
a[0,:]=np.round(a[0,:])
a[-1,:]=np.round(a[-1,:])
a[:,2]=np.flip(a[:,2])
a[:,3]=np.flip(a[:,3])



domain_vertices=[]


for j in range(len(a[:,0])):
    domain_vertices.append(Point(a[j,0],a[j,1],1))
for j in range(len(a[:,0])):
    domain_vertices.append(Point(a[j,2],a[j,3],1))
    



domain = mshr.Polygon(domain_vertices)
g=mshr.Extrude2D(domain,80)
mesh = generate_mesh(g, 200)


P2 = VectorElement("Lagrange", mesh.ufl_cell(), 2)
P1 = FiniteElement("Lagrange", mesh.ufl_cell(), 1)
TH = P2 * P1
W = FunctionSpace(mesh, TH)

# No-slip boundary condition for velocity
inflow  = 'near(x[1], 1162)'
outflow = 'near(x[1], 5170)'
walls   = 'on_boundary'

# Define boundary conditions
noslip  = DirichletBC(W.sub(0), Constant((0, 0,0)), walls)
inflow  = DirichletBC(W.sub(1), Constant(10), inflow)
outflow = DirichletBC(W.sub(1), Constant(0), outflow)




bcs = [noslip, inflow,outflow]

# Define variational problem
(u, p) = TrialFunctions(W)
(v, q) = TestFunctions(W)
f = Constant((0, 0,0))
a = (inner(grad(u), grad(v)) - div(v)*p + q*div(u))*dx
L = inner(f, v)*dx
w = Function(W)
#F = inner(grad(u)*u, v)*dx + nu*inner(grad(u), grad(v))*dx \
#     - inner(p, div(v))*dx + inner(q, div(u))*dx + inner(f, v)*dx

solve(a == L, w, bcs)

# Split the mixed solution using a shallow copy
(u, p) = w.split()

##################################################################### vtkplotter
f = r'-\nabla \cdot(\nabla u+p I)=f ~\mathrm{in}~\Omega'
formula = Latex(f, pos=(0.55,0.45,-.05), s=0.1)

plot(u, formula, at=0, N=2,
     mode='mesh ', scale=10,
     wireframe=True, scalarbar=False, style=1)
plot(p, at=1, text="pressure", cmap='rainbow')

'''
##################################################################### streamlines
# A list of seed points (can be automatic: just comment out 'probes')
ally = np.linspace(0,50, num=100)
probes = np.c_[np.ones_like(ally), ally, np.zeros_like(ally)]

plot(u, 
     mode='mesh with streamlines',
     streamlines={'tol':0.1,            # control density of streams
                  'lw':1,                # line width 
                  'direction':'forward', # direction of integration
                  'maxPropagation':18,  # max length of propagation
                  'probes':probes,       # custom list of point in space as seeds
                 },
     c='white',                          # mesh color
     alpha=0.3,                          # mesh alpha
     lw=0,                               # mesh line width
     wireframe=True,                     # show as wireframe
     bg='blackboard',                    # background color
     newPlotter=True,                    # new window
     pos=(200,200),                      # window position on screen
     )
     '''
