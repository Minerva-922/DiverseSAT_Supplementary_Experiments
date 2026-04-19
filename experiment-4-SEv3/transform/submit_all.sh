#!/bin/bash
# experiment-4 transform submission (SEv3-alone)

sbatch jobslurm-2_OH_SEv3
sleep 1

sbatch jobslurm-2_UNA_SEv3
sleep 1

sbatch jobslurm-2_BIN_SEv3
sleep 1

sbatch jobslurm-3_OH_SEv3
sleep 1

sbatch jobslurm-3_UNA_SEv3
sleep 1

sbatch jobslurm-3_BIN_SEv3
sleep 1

sbatch jobslurm-4_OH_SEv3
sleep 1

sbatch jobslurm-4_UNA_SEv3
sleep 1

sbatch jobslurm-4_BIN_SEv3
sleep 1

sbatch jobslurm-5_OH_SEv3
sleep 1

sbatch jobslurm-5_UNA_SEv3
sleep 1

sbatch jobslurm-5_BIN_SEv3
sleep 1

sbatch jobslurm-10_OH_SEv3
sleep 1

sbatch jobslurm-10_UNA_SEv3
sleep 1

sbatch jobslurm-10_BIN_SEv3
sleep 1

