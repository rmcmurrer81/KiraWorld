# Hardware Intake And Rested Build Gate v1

This is for the moment Robert gets home from the Micro Center trip.

The goal is simple:

```text
get home
put CPU/RAM/prizes somewhere safe
do not build tired
sleep
recover
build only after the rest gate passes
```

## Immediate Return-Home Rule

When Robert gets home with the Intel Core Ultra 9 285:

```text
put the CPU box flat on a dry stable table
keep receipts and claim tickets in one safe place
do not open the CPU box half-asleep
do not start the build
eat
drink water
go to bed
```

The CPU can wait. Kira can wait. Tiny expensive parts deserve steady hands.

## Main Check

Run:

```powershell
py tools\hardware_intake_check.py --show
```

This checks:

```text
hardware intake checklist validates
safe-storage rules exist
rest-before-build gate is active
CPU compatibility checks are listed
RAM can be missing without blocking project prep
do-not-build-tired rules exist
```

## Rested Build Gate

Do not assemble until these are true:

```text
not sleep deprived
hands steady
has eaten recently
water nearby but not next to parts
good lighting
enough uninterrupted time
not rushing
parts and tools organized
```

Allowed while tired:

```text
store parts safely
photograph receipts
write down CPU/RAM details
read docs
run project checks
```

Blocked while tired:

```text
opening CPU socket
installing CPU
installing RAM
installing cooler
plugging in power for first boot
```

## If RAM Does Not Happen Tomorrow

That is not a failure.

```text
store CPU safely
wait for RAM after May 15 or June 1
keep preparing Kira on the laptop
do not attempt a full build without RAM
```

## First Build Day

When rested:

```text
read motherboard manual CPU/RAM sections
confirm LGA1851 support
confirm DDR5 RAM
confirm cooler mount
confirm thermal paste
install CPU
install RAM
install cooler
connect storage/display/keyboard
first BIOS boot
confirm CPU/RAM/storage
check temperatures
stop if anything feels wrong
```

The win is not building fast. The win is building calmly.
