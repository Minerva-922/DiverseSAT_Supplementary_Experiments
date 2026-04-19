#!/bin/bash
# Batch submission script for all generated SLURM transform jobs (experiment-2, k=3,4)

echo 'Submitting jobslurm-3_OH_SEv1 (Job: 3Ov1, k=3, encode=OH, parallel=10)...'
sbatch jobslurm-3_OH_SEv1
sleep 1

echo 'Submitting jobslurm-3_UNA_SEv1 (Job: 3Uv1, k=3, encode=UNA, parallel=10)...'
sbatch jobslurm-3_UNA_SEv1
sleep 1

echo 'Submitting jobslurm-3_BIN_SEv1 (Job: 3Bv1, k=3, encode=BIN, parallel=10)...'
sbatch jobslurm-3_BIN_SEv1
sleep 1

echo 'Submitting jobslurm-4_OH_SEv1 (Job: 4Ov1, k=4, encode=OH, parallel=10)...'
sbatch jobslurm-4_OH_SEv1
sleep 1

echo 'Submitting jobslurm-4_UNA_SEv1 (Job: 4Uv1, k=4, encode=UNA, parallel=10)...'
sbatch jobslurm-4_UNA_SEv1
sleep 1

echo 'Submitting jobslurm-4_BIN_SEv1 (Job: 4Bv1, k=4, encode=BIN, parallel=10)...'
sbatch jobslurm-4_BIN_SEv1
sleep 1

