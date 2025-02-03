# -*- coding: mbcs -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *
import os
import sys
import numpy as np
import csv

class AbaqusCAE:
    def __init__(self, model_name):
        self.model_name = model_name
        self.current_dir, self.work_dir = self.setup_directories()
        self.cae_path = self.current_dir + "\\" + self.model_name + ".cae"
        self.fortran_path = self.current_dir + "\\" + "VUSDFLD.for"
        self.model = self.open_and_copy_model()

    def setup_directories(self):
        current_dir = os.getcwd()
        work_dir = current_dir + "\\WD"
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        return current_dir, work_dir

    def print_paths(self):
        print >> sys.__stdout__, "Current directory:", self.current_dir
        print >> sys.__stdout__, "CAE path:", self.cae_path
        print >> sys.__stdout__, "Fortran path:", self.fortran_path
        print >> sys.__stdout__, "Work directory:", self.work_dir
        print >> sys.__stdout__, mdb.models.keys()

    def open_and_copy_model(self):
        mdb.openAuxMdb(pathName=self.cae_path)
        mdb.copyAuxMdbModel(fromName=self.model_name, toName=self.model_name)
        mdb.closeAuxMdb()
        return mdb.models[self.model_name]

    def modify_mesh(self, mesh_size=20.0, deviation_factor=0.1, min_size_factor=0.1):
        part = self.model.parts["Plate"]
        part.deleteMesh()
        part.seedPart(deviationFactor=deviation_factor, minSizeFactor=min_size_factor, size=mesh_size)
        part.generateMesh()

    def modify_step(self, step_time=0.004, max_increment=1e-05):
        self.model.rootAssembly.regenerate()
        self.model.steps["Step-1"].setValues(maxIncrement=max_increment, timePeriod=step_time)

    def modify_interaction(self, friction_coefficient=0.35):
        self.model.interactionProperties["IntProp-1"].tangentialBehavior.setValues(
            dependencies=0, directionality=ISOTROPIC, elasticSlipStiffness=None,
            formulation=PENALTY, fraction=0.005, maximumElasticSlip=FRACTION,
            pressureDependency=OFF, shearStressLimit=None, slipRateDependency=OFF,
            table=((friction_coefficient,),), temperatureDependency=OFF
        )

    def modify_predefined_fields(self,  velocity=-30000.0):
        self.model.predefinedFields["Velocity"].setValues(omega=0.0, velocity1=0.0, velocity2=0.0, velocity3=velocity)

    def create_and_submit_job(self, job_name, num_cpus=6):
        mdb.Job(
            activateLoadBalancing=False, atTime=None, contactPrint=OFF, description="",
            echoPrint=OFF, explicitPrecision=SINGLE, historyPrint=OFF, memory=90,
            memoryUnits=PERCENTAGE, model=self.model_name, modelPrint=OFF,
            multiprocessingMode=DEFAULT, name=job_name, nodalOutputPrecision=SINGLE,
            numCpus=num_cpus, numDomains=num_cpus, parallelizationMethodExplicit=DOMAIN,
            queue=None, resultsFormat=ODB, scratch="", type=ANALYSIS, userSubroutine=self.fortran_path,
            waitHours=0, waitMinutes=0
        )
        mdb.jobs[job_name].submit(consistencyChecking=OFF)
        mdb.jobs[job_name].waitForCompletion()

    def post_process(self, job_name):
        session.Viewport(name="Viewport: 1", origin=(0.0, 0.0), width=196.03125, height=238.829635620117)
        session.viewports["Viewport: 1"].makeCurrent()
        session.viewports["Viewport: 1"].maximize()

        a = self.model.rootAssembly
        session.viewports["Viewport: 1"].setValues(displayedObject=a)
        session.viewports["Viewport: 1"].assemblyDisplay.setValues(
            optimizationTasks=OFF, geometricRestrictions=OFF, stopConditions=OFF
        )

        session.viewports["Viewport: 1"].setValues(displayedObject=None)
        session.viewports["Viewport: 1"].partDisplay.geometryOptions.setValues(
            referenceRepresentation=ON
        )
        p = self.model.parts["Ball"]
        session.viewports["Viewport: 1"].setValues(displayedObject=p)

        o3 = session.openOdb(name=(self.work_dir + "\\" + job_name + ".odb"))
        session.viewports["Viewport: 1"].setValues(displayedObject=o3)
        session.viewports["Viewport: 1"].odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
        session.viewports["Viewport: 1"].viewportAnnotationOptions.setValues(
            legendFont="-*-verdana-medium-r-normal-*-*-180-*-*-p-*-*-*"
        )
        session.printToFile(fileName=(job_name + ".png"), format=PNG, canvasObjects=(
            session.viewports["Viewport: 1"],
        ))

        # Extract velocity in V3 direction for node set "REFERANCE_POINT_BALL-1"
        step_name = o3.steps.keys()[-1]  # Get the last step
        last_frame = o3.steps[step_name].frames[-1]  # Get the last frame
        velocity_field = last_frame.fieldOutputs['V']  # Velocity field output
        
        node_set = o3.rootAssembly.nodeSets['REFERENCE_POINT_BALL-1     1324']
        velocity = velocity_field.getSubset(region=node_set.nodes[0][0]).values[0].data  # Extract velocity components

        print >> sys.__stdout__, "Velocity in V3 direction for node {}: {} m/s".format(node_set.nodes[0][0].label, velocity[2]/1000)   # Print V3 component
        return velocity[2]/1000
        
        
        o3.close()

    def modify_thickness(self, thickness):
        self.model.parts['Plate'].features['Solid extrude-1'].setValues(
            depth=thickness)
        self.model.parts['Plate'].regenerate()

    # Function to update the CSV file
    def update_csv(self, job_name, friction, velocity, residual_vel, thickness, csv_file="job_data.csv"):
        # Check if the file exists
        file_exists = os.path.isfile(self.current_dir + "\\" + csv_file)
        
        # Open the file in append mode
        with open(self.current_dir + "\\" + csv_file, mode='a') as file:  # Removed 'newline' parameter
            writer = csv.writer(file)
            
            # Write the header if the file is being created for the first time
            if not file_exists:
                writer.writerow(["Job Name", "Friction", "Velocity", "Residual Velocity", "Thickness"])
            
            # Convert numpy.float64 to native Python float
            friction = float(friction)
            velocity = float(velocity)
            residual_vel = float(residual_vel)
            thickness = float(thickness)
            
            # Write the job data
            writer.writerow([job_name, friction, velocity, residual_vel, thickness])
