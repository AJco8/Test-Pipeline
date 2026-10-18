# Engine Test Analysis Pipeline

Full analysis for rocket engine test data.
- Imports telemetry from a test firing
- Synchronizes multiple sensors
- Filters noise
- Calculates derived parameters
- Flags anomalies

![](./Test%20Pipeline.jpg)

## Example parameters:
- chamber pressure
- thrust
- propellant mass flow rate
- mixture ratio
- injector pressure drop
- engine temperature

## Example outputs:
### Plots
##### Thrust vs Time
![](./out/Plots/Thrust.png)
#### Chamber Pressure vs Time
![](./out/Plots/Pc.png)
#### Mixture Ratio vs Time
![](./out/Plots/Mix%20Ratio.png)
#### Isp (Calculated)
![](./out/Plots/Specific%20Impulse.png)
- anomaly detection system
![](./out/Plots/Anomalies.md)


