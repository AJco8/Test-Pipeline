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

def load_data(path:str)->pd.DataFrame:
    """Converts telemetry CSV file into Pandas Dataframe

    Args:
        path (Path): Path to telemetry CSV file

    Raises:
        ValueError: time column is required

    Returns:
        pandas.DataFrame: Telemetry DataFrame
    """
    df = pd.read_csv(path)

    #convert all data to numeric    
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    #TODO need to automatically cut out rows where time = NaN

    return df

# Process Data
from time_series import butterworth, find_offset, offset

def uniform_resample(df: pd.DataFrame, dt: float, time_col: str="time") -> pd.DataFrame:
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
            df[col] = offset(t, sig, time_offset)
        #df.attrs["estimated_offset"][col] = time_offset
    return df

def filter(data:pd.DataFrame,rate):
    """Filter data to remove outliers and errors

    Args:
        data (pandas.DataFrame): Data to be filtered
        rate (float|int): Desired rate of sampling

    Returns:
        pandas.DataFrame: DataFrame with usable data
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
    
    #Mass Flow Rate + Mix Ratio
    if in_df(data,"dm_total"):
        dm_total = data["dm_total"]
    elif in_df(data,"dm_ox","dm_fuel"):
        dm_ox = data["dm_ox"].to_numpy(dtype=float)
        dm_fuel = data["dm_fuel"].to_numpy(dtype=float)
        dm_total = dm_ox + dm_fuel
        params['dm_total'] = dm_total

        mr = np.full(dm_ox.shape,np.nan)
        for i in range(mr.size):
            if dm_ox[i]>1e-6 and dm_fuel[i]>1e-6:
                mr[i] = dm_ox[i] / dm_fuel[i]
        params['Mix Ratio'] = mr
    else: 
        print("No mass flow rate column in DataFrame")
        return pd.DataFrame(params)

    #Specific Impulse
    thrust = data["thrust"].to_numpy(dtype=float)
    Isp = np.zeros(dm_total.shape)
    Isp[dm_total>0] = thrust[dm_total>0] / (dm_total[dm_total>0] * 9.81)
    params['Specific Impulse'] = Isp
    
    return pd.DataFrame(params)

# Plotting
import matplotlib.pyplot as plt
def time_plot(df:pd.DataFrame, y_col:str, x_col:str="time",out:str="Plots",show=False,names=None)->None:
    """Plots given column against time"""
    plt.figure()
    plt.plot(df[x_col].to_numpy(dtype=float),df[y_col].to_numpy(dtype=float))
    plt.xlabel("Time")
    if names:
        plt.ylabel(names[y_col])
    else:
        plt.ylabel(y_col)
    plt.savefig(f"{out}/{y_col}")
    if show: plt.show()

# Main Pipeline
def pipeline(telem_data:pd.DataFrame,rate:float|int,names:dict=None,reference:str=None,output="out"): # pyright: ignore[reportArgumentType]
    """Main Pipeline

    Args:
        telem_data (pd.DataFrame): Telemetry Data
        output (str, optional): Folder for output data and plots, defaults to "out".

    Raises:
        ValueError: Time column required
    """
    
    dt = 1/rate

    # Process Data
    if names:
        col_names = column_names
        rename = {value: key for key, value in col_names.items()}
        telem_data.rename(columns=rename, inplace=True)
    # Check if time column is included in CSV file  
    if "time" not in telem_data.columns:
        raise ValueError("Missing required time column")
    
    data = telem_data.sort_values("time").reset_index(drop=True)

    data = uniform_resample(telem_data,dt)

    if reference:
        ref_col = rename[reference]
        keys = [col for col in data.columns if col not in ["time",ref_col]]
        data = sync(data,dt,ref_col,*keys)

    data = filter(data,rate)

    # Derive Relavent Values
    params = parameters(data)
    
    out_data = pd.concat([data,params],axis=1)
    
    # Plot
    for col in out_data.columns:
        if col == "time": continue
        time_plot(out_data,col,out="out/Plots")

    # Save Everything
    out_data.to_csv(output+'/Parameters.csv', index=False)
    print(out_data)


if __name__ == "__main__":
    name = {
        'Chamber Pressure': 'Pc',
        'Thrust': 'thrust',
        'Oxygen Mass Flow Rate':'dm_ox', 
        'Fuel Mass Flow Rate': 'dm_fuel', 
        'Total Mass Flow Rate': 'dm_total', 
        'Oxygen Injector Pressure': 'Pinj_ox', 
        'Fuel Injector Pressure': 'Pinj_fuel', 
        'Injector Pressure': 'Pinj', 
        'Engine Temp': 'temp_engine', 
        'Coolant Pressure': 'Pcool',
        'Specific Impulse': 'Isp'
        }
    column_names = {
        "time": "time_s",
        "Pc": "pc_pa",
        "thrust": "thrust_n",
        "dm_ox": "mdot_ox_kg_s",
        "dm_fuel": "mdot_fuel_kg_s",
        "Pinj_ox": "pinj_ox_pa",
        "temp_engine": "temp_engine_k",
        "Pcool": "pcool_pa"
    }
    rate = 200 #Hz
    reference = "pc_pa"
    data = load_data("data/simulated_telemetry.csv")
    pipeline(data,rate,column_names,reference)