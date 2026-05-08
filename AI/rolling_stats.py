import numpy as np
import pandas as pd
from typing import Optional, Union, Dict, List, Tuple


def rolling_mean_std(
    data: Union[pd.DataFrame, pd.Series, np.ndarray],
    window: int,
    min_periods: Optional[int] = None,
    center: bool = False,
    ddof: int = 0,
) -> Union[pd.DataFrame, pd.Series, Tuple[np.ndarray, np.ndarray]]:
    """
    计算一组宏观经济时间序列的滚动均值和标准差。

    参数
    ----------
    data : pd.DataFrame, pd.Series, or np.ndarray
        宏观经济时间序列数据。
        - DataFrame: 每列为一个时间序列
        - Series: 单个时间序列
        - ndarray: 二维数组 (行=时间, 列=序列) 或一维数组 (单个序列)
    window : int
        滚动窗口大小（观测值个数）。
    min_periods : int, optional
        窗口内所需的最小观测值数量，用于计算统计量。
        默认值为 window（即窗口填满后才开始计算）。
    center : bool, default=False
        如果为 True，则将窗口中心对齐到当前观测值；
        如果为 False，则窗口右对齐（使用过去 window-1 个值 + 当前值）。
    ddof : int, default=0
        标准差计算中的自由度修正（Delta Degrees of Freedom）。
        对于总体标准差使用 ddof=0，样本标准差使用 ddof=1。

    返回
    -------
    如果输入为 DataFrame 或 Series，返回 DataFrame 或 Series（多级列索引，第一级为 'mean' 和 'std'）。
    如果输入为 ndarray，返回 (rolling_means, rolling_stds) 的元组。

    示例
    --------
    >>> import pandas as pd
    >>> import numpy as np

    >>> # 示例 1: DataFrame 输入
    >>> df = pd.DataFrame({
    ...     'GDP': np.random.randn(100),
    ...     'CPI': np.random.randn(100),
    ...     'UNEMP': np.random.randn(100)
    ... })
    >>> result = rolling_mean_std(df, window=12)
    >>> result['mean']['GDP'].head()

    >>> # 示例 2: Series 输入
    >>> s = pd.Series(np.random.randn(100), name='GDP')
    >>> result = rolling_mean_std(s, window=12)

    >>> # 示例 3: ndarray 输入
    >>> arr = np.random.randn(100, 3)
    >>> means, stds = rolling_mean_std(arr, window=12)

    >>> # 示例 4: 使用样本标准差
    >>> result = rolling_mean_std(df, window=12, ddof=1)

    >>> # 示例 5: 中心对齐窗口
    >>> result = rolling_mean_std(df, window=12, center=True)
    """
    # --- 输入验证 ---
    if not isinstance(window, int) or window < 1:
        raise ValueError(f"window 必须为正整数，得到 {window}")

    if min_periods is not None and (not isinstance(min_periods, int) or min_periods < 1):
        raise ValueError(f"min_periods 必须为正整数，得到 {min_periods}")

    if not isinstance(ddof, int) or ddof < 0:
        raise ValueError(f"ddof 必须为非负整数，得到 {ddof}")

    # --- 处理 ndarray 输入 ---
    if isinstance(data, np.ndarray):
        if data.ndim == 1:
            data_2d = data.reshape(-1, 1)
            single_col = True
        elif data.ndim == 2:
            data_2d = data
            single_col = False
        else:
            raise ValueError(
                f"ndarray 输入必须为 1 维或 2 维，得到 {data.ndim} 维"
            )

        n_obs, n_series = data_2d.shape

        if window > n_obs:
            raise ValueError(
                f"window ({window}) 不能超过观测值数量 ({n_obs})"
            )

        effective_min_periods = min_periods if min_periods is not None else window

        means = np.full_like(data_2d, np.nan, dtype=np.float64)
        stds = np.full_like(data_2d, np.nan, dtype=np.float64)

        for i in range(n_obs):
            if center:
                half = window // 2
                start = max(0, i - half)
                end = min(n_obs, i + half + (window % 2))
            else:
                start = max(0, i - window + 1)
                end = i + 1

            n_valid = end - start

            if n_valid >= effective_min_periods:
                means[i, :] = np.nanmean(data_2d[start:end, :], axis=0)
                stds[i, :] = np.nanstd(data_2d[start:end, :], axis=0, ddof=ddof)

        if single_col:
            means = means.flatten()
            stds = stds.flatten()

        return means, stds

    # --- 处理 pandas 输入 ---
    if isinstance(data, pd.Series):
        series_name = data.name or 'series'
        df_input = data.to_frame(series_name)
        is_series = True
    elif isinstance(data, pd.DataFrame):
        df_input = data
        is_series = False
    else:
        raise TypeError(
            f"data 必须为 pd.DataFrame、pd.Series 或 np.ndarray，"
            f"得到 {type(data).__name__}"
        )

    # 检查索引是否为 datetime 类型
    if not isinstance(df_input.index, pd.DatetimeIndex):
        import warnings
        warnings.warn(
            "输入数据的索引不是 DatetimeIndex。"
            "滚动计算将基于行位置而非时间频率进行。"
        )

    effective_min_periods = min_periods if min_periods is not None else window

    # 计算滚动均值和标准差
    rolling_obj = df_input.rolling(
        window=window,
        min_periods=effective_min_periods,
        center=center,
    )

    rolling_means = rolling_obj.mean()
    rolling_stds = rolling_obj.std(ddof=ddof)

    # 构建多级列索引的结果
    if is_series:
        result = pd.DataFrame({
            ('mean', series_name): rolling_means.iloc[:, 0],
            ('std', series_name): rolling_stds.iloc[:, 0],
        })
    else:
        arrays = []
        for col in df_input.columns:
            arrays.append(('mean', col))
            arrays.append(('std', col))

        result = pd.DataFrame(
            np.column_stack([
                rolling_means[col] for col in df_input.columns
            ] + [
                rolling_stds[col] for col in df_input.columns
            ]),
            index=df_input.index,
            columns=pd.MultiIndex.from_tuples(arrays),
        )

    return result


def rolling_mean_std_with_dates(
    data: Union[pd.DataFrame, pd.Series],
    window: int,
    min_periods: Optional[int] = None,
    center: bool = False,
    ddof: int = 0,
) -> pd.DataFrame:
    """
    计算带日期索引的宏观经济时间序列的滚动均值和标准差。
    要求输入数据具有 DatetimeIndex。

    参数
    ----------
    data : pd.DataFrame or pd.Series
        具有 DatetimeIndex 的时间序列数据。
    window : int
        滚动窗口大小（以观测值个数计）。
    min_periods : int, optional
        窗口内所需的最小观测值数量。
    center : bool, default=False
        是否将窗口中心对齐。
    ddof : int, default=0
        标准差自由度修正。

    返回
    -------
    pd.DataFrame
        包含滚动均值和标准差的结果，具有多级列索引。
    """
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("输入数据必须具有 DatetimeIndex")

    return rolling_mean_std(
        data=data,
        window=window,
        min_periods=min_periods,
        center=center,
        ddof=ddof,
    )


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    # 生成模拟的宏观经济数据
    np.random.seed(42)
    n_obs = 200

    dates = pd.date_range(start="2000-01-01", periods=n_obs, freq="M")

    macro_data = pd.DataFrame(
        {
            "GDP_Growth": np.random.normal(0.02, 0.01, n_obs),
            "CPI_Inflation": np.random.normal(0.03, 0.005, n_obs),
            "Unemployment": np.random.normal(0.05, 0.02, n_obs),
            "Interest_Rate": np.random.normal(0.04, 0.01, n_obs),
        },
        index=dates,
    )

    print("原始数据前 5 行：")
    print(macro_data.head())
    print("\n" + "=" * 60)

    # 计算 12 期滚动均值和标准差
    result = rolling_mean_std(macro_data, window=12)

    print("\n滚动统计量（前 15 行）：")
    print(result.head(15))
    print("\n" + "=" * 60)

    # 使用样本标准差
    result_sample = rolling_mean_std(macro_data, window=12, ddof=1)

    print("\n使用样本标准差（ddof=1）的滚动统计量（前 15 行）：")
    print(result_sample.head(15))
    print("\n" + "=" * 60)

    # 中心对齐窗口
    result_centered = rolling_mean_std(macro_data, window=12, center=True)

    print("\n中心对齐窗口的滚动统计量（前 15 行）：")
    print(result_centered.head(15))
    print("\n" + "=" * 60)

    # 单个序列
    single_series = macro_data["GDP_Growth"]
    result_single = rolling_mean_std(single_series, window=12)

    print("\n单个序列的滚动统计量（前 15 行）：")
    print(result_single.head(15))
    print("\n" + "=" * 60)

    # ndarray 输入
    arr = macro_data.values
    means, stds = rolling_mean_std(arr, window=12)

    print(f"\nndarray 输入 - 均值形状: {means.shape}, 标准差形状: {stds.shape}")
    print("前 5 行的均值：")
    print(means[:5])
    print("\n前 5 行的标准差：")
    print(stds[:5])