# -*- coding: mbcs -*-

import os
from AbaqusCAE import *


if __name__ == "__main__":

    velocity             = [129e3]#, 104e3]
    mesh_size            = 10.0
    step_time            = 0.002
    max_increment        = 1e-06

    friction_lower       = 0.2
    friction_upper       = 0.9
    friction_increment   = 0.5
    friction             = np.arange(friction_lower, friction_upper + friction_increment, friction_increment)

    thickness_lower       = 5.2
    thickness_upper       = 5.9
    thickness_increment   = 0.5
    thickness             = np.arange(thickness_lower, thickness_upper + thickness_increment, thickness_increment)
    
    # Create an object with model and job names
    cae = AbaqusCAE(model_name="Ball-Strike")

    # Print paths
    cae.print_paths()

    # Change directory to working directory
    os.chdir(cae.work_dir)

    # Modify mesh with custom parameters
    cae.modify_mesh(mesh_size=mesh_size, deviation_factor=0.1, min_size_factor=0.1)

    # Modify step parameters
    cae.modify_step(step_time=step_time, max_increment=max_increment)

    # Modify interaction (friction coefficient)
    cae.modify_interaction(friction_coefficient=friction[0])

    # Modify predefined field (velocity)
    cae.modify_predefined_fields(velocity=velocity[0])

    # Create and submit job with CPU settings
    for t in thickness:
        for v in velocity:
            for f in friction:

                cae.modify_thickness(thickness=t)
                cae.modify_mesh(mesh_size=mesh_size, deviation_factor=0.1, min_size_factor=0.1)
                cae.modify_predefined_fields(velocity=v)
                cae.modify_interaction(friction_coefficient=f)

                job_name = "Ball-Impact" + '-' + str(int(float(v/1000))) + '-' + str(f).replace('.', '') + '-' + str(t).replace('.', '')

                cae.create_and_submit_job(job_name=job_name,
                                        num_cpus=6)
                
                residual_vel = cae.post_process(job_name=job_name)
                
                # Update the CSV file with the job data

                print >> sys.__stdout__, "============================"
                print >> sys.__stdout__, "Residual velocity: ", residual_vel, " m/s"
                print >> sys.__stdout__, "Friction         : ", f
                print >> sys.__stdout__, "Velocity         : ", v/1000, " m/s"
                print >> sys.__stdout__, "Thickness        : ", t, " mm"
                print >> sys.__stdout__, "Job Name         : ", job_name
                print >> sys.__stdout__, "============================"

                cae.update_csv( job_name, f, v/1000, residual_vel, t)

