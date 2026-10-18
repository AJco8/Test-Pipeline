import numpy as np
import pandas as pd


def smooth_step(t, t0, t1):
    x = np.clip((t - t0) / max(t1 - t0, 1e-6), 0.0, 1.0)
    return x * x * (3 - 2 * x)


def telemetry() -> pd.DataFrame:
    rng = np.random.default_rng()

    # base timeline
    fs_native = 500
    t = np.arange(0.0, 8.0, 1.0 / fs_native)

    # valve opens ~1.5s, shutdown ~6.5s
    rise = smooth_step(t, 1.5, 2.0)
    fall = 1 - smooth_step(t, 6.3, 6.7)
    gate = rise * fall

    pc_peak = 10e6
    pc = gate * (pc_peak * (0.9 + 0.1 * np.sin(2 * np.pi * 0.8 * t)))
    pc += rng.normal(0.0, 0.03 * pc_peak, size=t.size)  # noise
    pc = np.clip(pc, 0, None)

    # flows
    dm_total = gate * 4.0  # kg/s
    mr_true = 2.6 + 0.1 * np.sin(2 * np.pi * 0.5 * t) * gate
    dm_fuel = dm_total / (1.0 + mr_true)
    dm_ox = dm_total - dm_fuel

    dm_ox += rng.normal(0.0, 0.03, size=t.size)
    dm_fuel += rng.normal(0.0, 0.02, size=t.size)
    dm_ox = np.clip(dm_ox, 0, None)
    dm_fuel = np.clip(dm_fuel, 0, None)

    # thrust
    thrust = 0.08 * pc
    thrust += rng.normal(0.0, 0.02 * np.nanmax(thrust + 1e-9), size=t.size)

    # injector pressure
    dp_inj = gate * (0.8e6 + 0.1e6 * np.sin(2 * np.pi * 1.5 * t))
    pinj_ox = pc + dp_inj + rng.normal(0.0, 0.02e6, size=t.size)

    # coolant line pressure
    pcool = pc + gate * 0.3e6 + rng.normal(0.0, 0.01e6, size=t.size)

    # engine temp
    temp = 300.0 + gate * 650.0
    temp += rng.normal(0.0, 5.0, size=t.size)

    # Add anomalies
    # injector P drop
    glitch = (t > 4.2) & (t < 4.28)
    pinj_ox[glitch] -= 0.9e6

    # thrust spike
    spike = (t > 5.1) & (t < 5.13)
    thrust[spike] += 0.25 * np.nanmax(thrust)

    df = pd.DataFrame({
        "time": t,
        "pc": pc,
        "thrust": thrust,
        "dm_ox": dm_ox,
        "dm_fuel": dm_fuel,
        "pinj_ox": pinj_ox,
        "temp_engine": temp,
        "pcool": pcool
    })

    # time offsets to simulate DAQ clocks
    # thrust delayed by 60 ms/flows advanced by 40 ms
    def shift(col, dt_s):
        tt = df["time"].to_numpy()
        yy = df[col].to_numpy()
        df[col] = np.interp(tt, tt - dt_s, yy, left=np.nan, right=np.nan)

    shift("thrust", dt_s=0.060)
    shift("dm_ox", dt_s=-0.040)
    shift("dm_fuel", dt_s=-0.040)

    return df

if __name__ == "__main__":
    data = telemetry()
    data.to_csv("./data/Simulation.csv", index=False)
