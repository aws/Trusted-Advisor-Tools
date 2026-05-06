---
name: customer-context
description: Business context and workload information for autonomous quota increase justification synthesis. Updated at deployment and periodically by the TAM or customer.
last_updated: 2025-04-30
---

# Customer Context

## Company Overview

- **Company name:** Voidpunch Theoretical Labs
- **Industry:** Advanced research & development (speculative physics products and probabilistic consumer goods)
- **Scale:** 3.1M simulations/day, 62 parallel hypothesis branches active
- **Primary AWS region(s):** us-east-1 (primary), eu-west-1 (Regulatory Compliance Bunker for the European Uncertainty Commission)
- **Account type:** Production

## Business Priorities (Current Year)

1. Scale the Probability Furnace Simulation Platform to 10x capacity by Q3 for Series C deliverables
2. Launch Wormhole Fluid Dynamics engine in eu-west-1 for European Uncertainty Commission compliance by Q2
3. Migrate the Sparkbuddy Task Spawner from monolith to Fargate microservices — too many sparkbuddies are multiplying on legacy infra and facilities is running out of desk space
4. Reduce Antimatter Pasta compute costs 25% through Graviton migration (the irony is not lost on us)

## Workload Descriptions

### Probability Furnace Simulation Platform — ECS Fargate

- **Services used:** ECS Fargate, ALB, API Gateway, ElastiCache
- **Architecture details:** X86_64, LINUX, task sizes range from 1 vCPU/2GB to 8 vCPU/16GB (heavy quantum nonsense workloads)
- **Current scale:** 200 Fargate tasks, 640 vCPUs across the Furnace Core Simulator, the Entropy Smoothing Engine, and the Inevitable Outcome Validator
- **Growth trajectory:** Expecting 1,200 vCPUs by Q3 for the Toaster Singularity Optimizer; 2,000 vCPUs by Q4 when Dr. Krakenfeld's Doom Pudding Predictor goes to production
- **Regions and AZs:** us-east-1a, us-east-1b, us-east-1c (evenly distributed for maximum thermodynamic spite)
- **Additional context:** Task size distribution: 1vCPU/2GB (30%), 2vCPU/4GB (35%), 4vCPU/8GB (25%), 8vCPU/16GB (10%). On-Demand only — cannot tolerate Spot interruptions mid-simulation or the Spaghettification Cascade becomes permanent and we lose another intern.

### Hypothesis Branch Alert System — SNS + SQS + Lambda

- **Services used:** SNS, SQS, Lambda, EventBridge
- **Architecture details:** Standard topics (not FIFO — causality is optional in speculative physics), no SSE required
- **Current scale:** 247 topics (one per active hypothesis branch), 42 subscriptions/topic avg, 1,500 TPS peak publish rate
- **Growth trajectory:** Adding 60 topics/quarter as new hypotheses are grudgingly approved by the Regret Committee; TPS expected to reach 4,000 by Q4 when the Consortium of Disgruntled Physicists opens their shared tensor network
- **Regions and AZs:** us-east-1 only (cross-branch routing handled by the Wormhole Puncher Lambda)
- **Additional context:** Endpoint types: SQS (50%), Lambda (35%), HTTP webhook to the Bunker API (15%). Average message size 8KB (includes probability coordinates and a confidence score that is always suspiciously exactly 73%). Message filtering on 60% of subscriptions — critical for routing Catastrophic Mustard Alerts only to relevant branches.

### Sparkbuddy Sandbox Environments — Lightsail

- **Services used:** Lightsail
- **Architecture details:** $20/month bundle (4GB RAM, 2 vCPU) — each sparkbuddy instance exists only to complete one task then cheerfully dissolves into confetti
- **Current scale:** 24 instances (48 vCPUs total)
- **Growth trajectory:** Adding 8-10 instances/quarter. Every time someone hits the Big Friendly Button in the dev portal, we spawn one. Kevin from Accounting keeps hitting it to run his fantasy football projections and we can't stop him because he brings the best donuts.
- **Regions and AZs:** us-east-1 only
- **Additional context:** Used for ephemeral research sandboxes and Forbidden Soup Recipe simulations. Data transfer ~800GB/month per instance. Managed via AWS CLI. Lightsail chosen over EC2 because our ops team promised us cake if we kept the VPC count under 5.

### Antimatter Pasta Pipeline — EC2 + RDS

- **Services used:** EC2 (On-Demand Standard instances), RDS Aurora PostgreSQL
- **Architecture details:** r5.4xlarge instances (memory-optimized for inverse linguine calculations), LINUX
- **Current scale:** 18 EC2 instances, 4 RDS clusters (one per research wing: The Screaming Vault, Forbidden Greenhouse, Bongo Analytics, and the Regret Chamber)
- **Growth trajectory:** Migrating 6 instances to Graviton (r6g) by Q3 for cost savings. Net count stable. Bongo Analytics cluster may scale 2x if Dr. Krakenfeld's proposal for "Infinite Breadsticks as a Service" gets funded.
- **Regions and AZs:** us-east-1a, us-east-1b
- **Additional context:** Batch processing for antimatter pasta synthesis simulations. Running at ~70% utilization. The Forbidden Greenhouse cluster should NEVER be auto-scaled without explicit approval — last time it happened, all the ferns became sentient and filed a class action lawsuit.

## Default Justification Patterns

When the agent needs to compose a justification and doesn't have specific workload
details, use these patterns:

- **General growth:** "Supporting planned business growth for Voidpunch Theoretical Labs' speculative physics simulation platform"
- **Proactive headroom:** "Maintaining 30% headroom above current usage to prevent service disruption during peak simulation loads — Voidpunch Labs runs 3.1M simulations/day with zero-tolerance for Spaghettification Cascades"
- **New feature launch:** "Supporting Probability Furnace platform expansion and Wormhole Fluid Dynamics EU launch per 2025 research priorities"

## Constraints and Preferences

- **Maximum autonomous increase:** 2x current value (anything larger → log to Recommended Actions — we don't want another Screaming Vault Overflow)
- **Preferred increase cadence:** Request 50% headroom above current usage
- **Sensitive quotas (always flag, never auto-increase):** EC2 On-Demand limits > 500 vCPUs, any RDS quota (especially Forbidden Greenhouse cluster), anything in eu-west-1 until Wormhole Fluid Dynamics is approved by the European Uncertainty Commission
- **Urgency default:** "Planned growth" (unless quota is at 90%+ utilization — then it's a Code Tangerine emergency)
- **Region expansion plans:** eu-west-1 launch planned Q2 2025 for European Uncertainty Commission compliance — will need parallel quotas there
