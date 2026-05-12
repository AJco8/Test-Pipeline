import numpy as np
import pandas as pd
def in_df(df:pd.DataFrame,*cols:str)->bool:
    """Checks if columns are in DataFrame

    Args:
        df (pandas.DataFrame): DataFrame with named columns
        cols (str): Name of column

    Returns:
        bool: Column is in Dataframe
    """
    if False in [col in df.columns for col in cols]: return False
    else: return True

def load_data(path:str,colnames:dict)->pd.DataFrame:
    """Converts telemetry CSV file into Pandas Dataframe

    Args:
        path (Path): Path to telemetry CSV file

    Raises:
        ValueError: time column is required

    Returns:
        pandas.DataFrame: Telemetry DataFrame
    """
    df = pd.read_csv(path)
    df.rename(columns=colnames, inplace=True)

    # Check if time column is included in CSV file
    if "time" not in df.columns:
        raise ValueError("Missing required time column")

    #convert all data to numeric    
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by time
    df = df.sort_values("time").reset_index(drop=True)
    #TODO need to automatically cut out rows where time = NaN

    return df

# Process Data
from time_series import butterworth, find_offset, offset

def uniform_resample(df: pd.DataFrame, time_col: str, dt: float) -> pd.DataFrame:
    """Resample values to match a uniform time rate

    Args:
        df (pandas.DataFrame): time series Pandas Dataframe
        time_col (str): Name of column of Dataframe that records the time
        dt (float): length of time in between datapoints 

    Returns:
        pandas.DataFrame: Pandas Dataframe of time series data matching the uniform time rate
    """

    t = df[time_col].to_numpy(dtype=float)

    t_uniform = np.arange(min(t), max(t), dt)

    out = {time_col: t_uniform}

    for col in df.columns:
        # Skip time column
        if col == time_col:
            continue
        
        val = df[col].to_numpy() 
        mask = np.isfinite(val) # Indeces of finite values
        # If there are only 1 or no finite values: this column cannot be useful as a time series, set it all to NAN
        if mask.sum() < 2:
            out[col] = np.full_like(t_uniform, np.nan, dtype=float)
        else:
            # Interpolate to approximate value at this time
            out[col] = np.interp(t_uniform, t[mask], val[mask])
    return pd.DataFrame(out)

def sync(df:pd.DataFrame,dt,ref_col:str,*key_cols:str):
    """Synchronize data to correct of time offset

    Args:
        df (pandas.DataFrame): DataFrame with time-series columns
        dt (float): length of time in between datapoints 
        ref_col (str): Name of column to act as the reference to compare other columns

    Raises:
        IndexError: reference column is not found in DataFrame

    Returns:
        pandas.DataFrame: DataFrame with columns approximately time-synchronized
    """
    if ref_col not in data.columns:
        raise IndexError("Chosen reference column not in DataFrame")

    ref = df[ref_col].to_numpy()
    for col in key_cols:
        if col not in df.columns:
            print(f"Skipping {col}, not in provided DataFrame")
        sig = df[col].to_numpy()
        t = df["time"].to_numpy()

        time_offset = find_offset(ref, sig, dt, 0.5)
        if abs(time_offset) > 1e-6:
            df[col] = offset(t, sig, offset)
        df.attrs["estimated_offset"][col] = time_offset
    return df

def filter(data:pd.DataFrame,rate):
    """Filter data to remove outliers and errors

    Args:
        data (pandas.DataFrame): Data to be filtered
        rate (float|int): Desired rate of sampling

    Returns:
        pandas.DataFrame: _description_
    """
    for col in data.columns:
        #Time should not be filtered
        if col == "time":
            continue
        y = data[col].to_numpy(dtype=float)
        data[col] = butterworth(y, rate=rate, cutoff=25.0, order=4)
    
    return data

# Derive Values
def parameters(data:pd.DataFrame)->pd.DataFrame:
    # Output
    params = dict()

    # Pressure drop
    P_meas = ["Pinj","Pcool","Pox","Pfuel"] # Pressure measurments
    for i in P_meas:
        if in_df(data,i,"Pc"):
            params[i+' Drop'] = data[i]-data["Pc"]
        else:
            print(i+" column not in DataFrame")
    
    # Thermal Rate
    if in_df(data,"temp_engine"):
        t = data["time"].to_numpy(dtype=float)
        temp = data["temp_engine"].to_numpy(dtype=float)
        params["dtemp_dt"] = np.gradient(temp, t, edge_order=1)
    
    if in_df(data,"dm_total"):
        dm_total = data["dm_total"]
    elif in_df(data,"dm_ox","dm_fuel"):
        dm_ox = data["dm_ox"].to_numpy(dtype=float)
        dm_fuel = data["dm_fuel"].to_numpy(dtype=float)
        dm_total = dm_ox + dm_fuel
        params['dm_total'] = dm_total

        mr = np.full(dm_ox.shape,np.nan)
        for i in range(max(mr.size)):
            if dm_ox[i]>1e-6 and dm_fuel[i]>1e-6:
                mr[i] = dm_ox[i] / dm_fuel[i]
        params['Mix Ratio'] = mr

    else: 
        print("No mass flow rate column in DataFrame")
        return pd.DataFrame(params)


    thrust = data["thrust"].to_numpy(dtype=float)
    Isp = np.zeros(thrust.shape)
    Isp[dm_total>0] = thrust / (dm_total * 9.81)
    params['Specific Impulse'] = Isp
    
    return pd.DataFrame(params)

# Plotting
import matplotlib.pyplot as plt
def df_plot(df:pd.DataFrame, y_col:str, x_col:str="time",show=False)->None:
    plt.figure
    plt.plot(df[x_col].to_numpy(dtype=float),df[y_col].to_numpy(dtype=float))
    plt.xlabel("Time")
    plt.ylabel(y_col)
    if show: plt.show()

def plot_all(df):
    cols = df.columns
    time = df["time"].to_numpy(dtype=float)
    name = {
        "Pc": "P_c",
        "thrust": "F",
        "dm_ox": "dm_ox",
        "dm_fuel": "dm_fuel",
        "Pinj_ox": "P_{inj,ox}",
        "temp_engine": "T",
        "Pcool": "P_cool"
    }
    plt.figure()
    for i,col in enumerate(df.columns):
        if col == "time": continue
        plt.subplot(len(cols)-1,1,i)
        plt.plot(time,df[col].to_numpy(dtype=float))
        plt.xlabel("Time")
        plt.ylabel(col)
    plt.show()

if __name__ == "__main__":
    names = {
        "time": "time_s",
        "Pc": "pc_pa",
        "thrust": "thrust_n",
        "dm_ox": "mdot_ox_kg_s",
        "dm_fuel": "mdot_fuel_kg_s",
        "Pinj_ox": "pinj_ox_pa",
        "temp_engine": "temp_engine_k",
        "Pcool": "pcool_pa"
    }
    rename = {value: key for key, value in names.items()}
    data = load_data("data/simulated_telemetry.csv",rename)
    print("Loaded")
    params = parameters(data)
    print("Parameters")
    df_plot(pd.concat([data,params["Specific Impulse"]]),"Specific Impulse")
    #plot_all(pd.concat([data,params]))

    