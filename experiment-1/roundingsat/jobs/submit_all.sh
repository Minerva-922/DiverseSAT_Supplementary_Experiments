#!/bin/bash
# Batch submission script for all generated SLURM jobs
# Generated with FEWEST_TESTS mode enabled
# Total jobs: 12

echo 'Submitting jobslurm-2_OH_SEv1_roundingsat (Job: 2Ov1R, k=2, OH, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-2_OH_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-2_UNA_SEv1_roundingsat (Job: 2Uv1R, k=2, UNA, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-2_UNA_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-2_BIN_SEv1_roundingsat (Job: 2Bv1R, k=2, BIN, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-2_BIN_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-2_BIN_noSE_roundingsat (Job: 2BnoR, k=2, BIN, noSE, roundingsat, parallel=10)...'
sbatch jobslurm-2_BIN_noSE_roundingsat
sleep 1

echo 'Submitting jobslurm-5_OH_SEv1_roundingsat (Job: 5Ov1R, k=5, OH, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-5_OH_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-5_UNA_SEv1_roundingsat (Job: 5Uv1R, k=5, UNA, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-5_UNA_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-5_BIN_SEv1_roundingsat (Job: 5Bv1R, k=5, BIN, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-5_BIN_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-5_BIN_noSE_roundingsat (Job: 5BnoR, k=5, BIN, noSE, roundingsat, parallel=10)...'
sbatch jobslurm-5_BIN_noSE_roundingsat
sleep 1

echo 'Submitting jobslurm-10_OH_SEv1_roundingsat (Job: 10Ov1R, k=10, OH, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-10_OH_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-10_UNA_SEv1_roundingsat (Job: 10Uv1R, k=10, UNA, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-10_UNA_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-10_BIN_SEv1_roundingsat (Job: 10Bv1R, k=10, BIN, SEv1, roundingsat, parallel=10)...'
sbatch jobslurm-10_BIN_SEv1_roundingsat
sleep 1

echo 'Submitting jobslurm-10_BIN_noSE_roundingsat (Job: 10BnoR, k=10, BIN, noSE, roundingsat, parallel=10)...'
sbatch jobslurm-10_BIN_noSE_roundingsat
sleep 1

