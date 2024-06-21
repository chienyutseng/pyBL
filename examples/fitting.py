from pybl.utils.timeseries import preprocess_classic
from pybl.models import Stat_Props, BLRPRx_params, BLRPRx, BLRPRxConfig
import os
import pandas as pd
import numpy as np
import scipy as sp

timescale = np.array([1/12, 1, 3, 6])

# Set timezone to UTC
os.environ["TZ"] = "UTC"


def rain_timeseries():
    data_path = os.path.join(os.path.dirname(__file__), "data", "bochum_5min.csv")
    data = pd.read_csv(data_path, parse_dates=["datatime"])
    data["datatime"] = data["datatime"].astype("int64") // 10**9
    time = data["datatime"].to_numpy()
    intensity = data[list(data.keys())[-1]].to_numpy()
    return time, intensity


time, intensity = rain_timeseries()
# Check if time difference between each time step
diff = np.diff(time)
print(f"Max intensity: {np.max(intensity)}")
print(f"Min intensity: {np.min(intensity)}")
print(f"-1 count: {np.sum(intensity == -1)}")
print(len(time))
print(f"{np.unique(diff)}")

invalid_idxs = np.where(np.diff(time) <= 0)[0]

for invalid_idx in invalid_idxs:
    # Convert the time to epoch time in UTC
    print(f"Invalid time: {pd.to_datetime(time[invalid_idx-1], unit='s', utc=True)}")
    print(f"Invalid time: {pd.to_datetime(time[invalid_idx], unit='s', utc=True)}")
    print(f"Invalid time: {pd.to_datetime(time[invalid_idx+1], unit='s', utc=True)}")

# Prepare target and weight
target, weight = preprocess_classic(time, intensity, timescale=timescale)
print(f'Finished preprocessing, target shape: {target.shape}, weight shape: {weight.shape}')

# Optimize
for month in range(12):
    # Setting up the objective function
    target_df = BLRPRxConfig.default_target()
    target_df[Stat_Props.MEAN] = target[month, :, 0]
    target_df[Stat_Props.CVAR] = target[month, :, 1]
    target_df[Stat_Props.AR1] = target[month, :, 2]
    target_df[Stat_Props.SKEWNESS] = target[month, :, 3]

    weight_df = BLRPRxConfig.default_weight()
    weight_df[Stat_Props.MEAN] = weight[month, :, 0]
    weight_df[Stat_Props.CVAR] = weight[month, :, 1]
    weight_df[Stat_Props.AR1] = weight[month, :, 2]
    weight_df[Stat_Props.SKEWNESS] = weight[month, :, 3]

    mask_df = BLRPRxConfig.default_mask()
    mask_df[Stat_Props.MEAN] = [1, 0, 0, 0]
    mask_df[Stat_Props.CVAR] = [1, 1, 1, 1]
    mask_df[Stat_Props.AR1] = [1, 1, 1, 1]
    mask_df[Stat_Props.SKEWNESS] = [1, 1, 1, 1]

    fitter = BLRPRxConfig(target_df, weight_df, mask_df)

    obj = fitter.get_evaluation_func()

    # Fitting
    result = sp.optimize.dual_annealing(obj, bounds=[(0.000001, 20)] * 7, maxiter=10000)
    print(result)
    result_params = BLRPRx_params(*result.x)
    model = BLRPRx(result_params)
    for scale in timescale:
        print(model.get_prop(Stat_Props.MEAN, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.CVAR, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.AR1, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.SKEWNESS, timescale=scale))

    result = sp.optimize.dual_annealing(
        obj, bounds=[(0.000001, 20)] * 7, maxiter=10000, x0=result.x
    )
    print(result)
    result_params = BLRPRx_params(*result.x)
    model = BLRPRx(result_params)
    for scale in timescale:
        print(model.get_prop(Stat_Props.MEAN, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.CVAR, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.AR1, timescale=scale), end=" ")
        print(model.get_prop(Stat_Props.SKEWNESS, timescale=scale))
