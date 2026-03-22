#!/bin/bash
# Batch submission script for all generated SLURM jobs

echo 'Submitting jobslurm-2_OH_SEv1 (Job: 2Ov1, k=2, encode=OH, parallel=10)...'
sbatch jobslurm-2_OH_SEv1
sleep 1

echo 'Submitting jobslurm-2_UNA_SEv1 (Job: 2Uv1, k=2, encode=UNA, parallel=10)...'
sbatch jobslurm-2_UNA_SEv1
sleep 1

echo 'Submitting jobslurm-2_BIN_noSE (Job: 2Bv0, k=2, encode=BIN, parallel=10)...'
sbatch jobslurm-2_BIN_noSE
sleep 1

echo 'Submitting jobslurm-2_BIN_SEv1 (Job: 2Bv1, k=2, encode=BIN, parallel=10)...'
sbatch jobslurm-2_BIN_SEv1
sleep 1

echo 'Submitting jobslurm-5_OH_SEv1 (Job: 5Ov1, k=5, encode=OH, parallel=10)...'
sbatch jobslurm-5_OH_SEv1
sleep 1

echo 'Submitting jobslurm-5_UNA_SEv1 (Job: 5Uv1, k=5, encode=UNA, parallel=10)...'
sbatch jobslurm-5_UNA_SEv1
sleep 1

echo 'Submitting jobslurm-5_BIN_noSE (Job: 5Bv0, k=5, encode=BIN, parallel=10)...'
sbatch jobslurm-5_BIN_noSE
sleep 1

echo 'Submitting jobslurm-5_BIN_SEv1 (Job: 5Bv1, k=5, encode=BIN, parallel=10)...'
sbatch jobslurm-5_BIN_SEv1
sleep 1

echo 'Submitting jobslurm-10_OH_SEv1 (Job: 10Ov1, k=10, encode=OH, parallel=2)...'
sbatch jobslurm-10_OH_SEv1
sleep 1

echo 'Submitting jobslurm-10_UNA_SEv1 (Job: 10Uv1, k=10, encode=UNA, parallel=2)...'
sbatch jobslurm-10_UNA_SEv1
sleep 1

echo 'Submitting jobslurm-10_BIN_noSE (Job: 10Bv0, k=10, encode=BIN, parallel=2)...'
sbatch jobslurm-10_BIN_noSE
sleep 1

echo 'Submitting jobslurm-10_BIN_SEv1 (Job: 10Bv1, k=10, encode=BIN, parallel=2)...'
sbatch jobslurm-10_BIN_SEv1
sleep 1

