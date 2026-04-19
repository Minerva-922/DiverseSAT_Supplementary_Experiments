#!/bin/bash
# Batch submission script for all generated SLURM jobs (experiment-2, k=3,4)
# Total jobs: 6

echo 'Submitting jobslurm-3_OH_SEv1_roundingsat (Job: 3Ov1R, k=3, OH, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-3_OH_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-3_UNA_SEv1_roundingsat (Job: 3Uv1R, k=3, UNA, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-3_UNA_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-3_BIN_SEv1_roundingsat (Job: 3Bv1R, k=3, BIN, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-3_BIN_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-4_OH_SEv1_roundingsat (Job: 4Ov1R, k=4, OH, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-4_OH_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-4_UNA_SEv1_roundingsat (Job: 4Uv1R, k=4, UNA, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-4_UNA_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-4_BIN_SEv1_roundingsat (Job: 4Bv1R, k=4, BIN, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-4_BIN_SEv1_roundingsat
sleep 1

