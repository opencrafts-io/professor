# Getting started

Professor is a backend service responsible for institution data management and configuration for Academia platform's **Magnet** scraping engine.

## Purpose

The service provides the necessary metadata and instruction sets for Magnet to navigate institutional portals and collect student information.

## Core Concepts

### Institution
An institution in the Professor context is a college or university supported by the Academia platform to provide students with relevant information.

 - Scoping: All data is scoped to an institution. No Magnet command or student profile can exist without a parent institution record.
 - Sourcing: Institutions are primarily provided by Verisafe via a RabbitMQ event queue.

### Magnet

Magnet is a scraping engine designed to simulate human interaction on web-based applications and extract relevant information upon request.

  - Programmable Browser: Built on top of a programmable browser that runs in either headless or interactive mode.
  - Instruction Execution: It executes specific commands provided by Professor to navigate complex UI flows and extract valuable data points.

## System WorkflowSync

1. Sync: Professor listens to RabbitMQ for institution updates from Verisafe.
2. Configure: Our internal team define MagnetScrappingCommand objects containing JSON instructions.
3. Execute: Magnet queries Professor for these instructions and executes them against the target portal.
