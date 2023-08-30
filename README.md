# pvSavingSim
Simple Python script that simulates potential savings of your PV system based on PVGIS data

```
usage: pvSavingSim [-h] -i file -l N [-c N]

Simple script to simulate the possibel savings of your PV setup

options:
  -h, --help            show this help message and exit
  -i file, --pvgisTimeSeries file
                        Hourly consumption data exported from PVGIS in json format
  -l N, --inverterPowerLimit N
                        Maximum power of the inverter (in Watt)
  -c N, --constantConsumption N
                        The value of the constnat consumption that should be assumed (in Watt)
```
