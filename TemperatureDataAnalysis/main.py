import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
import numpy as np

data = None
data_statistics = None


def moving_average(x, w):
    return np.convolve(x, np.ones(w), mode='same') / w


def from_kelvin_to_celsius(temp):
    return temp - 273.15


st.header("Загрузка данных")

uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.session_state.data = data
    grouped_data = data.groupby(["city", "season"])
    data_statistics = grouped_data["temperature"].agg(["mean", "std"]).reset_index()
    st.write("Превью данных:")
    st.dataframe(data.head())
else:
    st.write("Пожалуйста, загрузите CSV-файл.")

if data is not None:
    st.divider()
    st.header("Визуализация данных")
    cities = data["city"].unique()
    options = st.multiselect(label="Выберите города", options=cities)
    data = data[data["city"].isin(options)]
    grouped_data = data.groupby(["city", "season"])
    agg_data = grouped_data["temperature"].agg(["mean", "std"])
    if st.button("Show"):
        st.line_chart(data, x="timestamp", y="temperature", color="city")
    if st.checkbox("Показать аномалии"):
        data['mean'] = grouped_data["temperature"].transform(lambda x: x.mean())
        data['std'] = grouped_data["temperature"].transform(lambda x: x.std())
        data["is_outlier"] = data[["temperature", "mean", "std"]].apply(
            lambda x: 1 if (x[0] > x[1] + 2 * x[2]) | (x[0] < x[1] - 2 * x[2]) else 0, axis=1)
        data_with_outliers = data[data["is_outlier"] == 1].drop(columns='is_outlier').reset_index(drop=True)
        st.dataframe(data_with_outliers)
    if st.checkbox("Показать статистики"):
        st.dataframe(agg_data, use_container_width=True)
    if st.checkbox("Сгладить график"):
        data['mov_avg'] = grouped_data["temperature"].transform(lambda x: moving_average(x, 30))
        st.line_chart(data, x="timestamp", y="mov_avg", color="city")

if data is not None:
    data = st.session_state.data
    st.divider()
    st.header("Текущая температура города")

    input_city = st.selectbox(label="Название города", options=data["city"].unique())
    input_api_key = st.text_input("API-ключ")
    if st.button("Показать погоду") and input_city and input_api_key:
        API_URL_COORDS = f"http://api.openweathermap.org/geo/1.0/direct?q={input_city}&appid={input_api_key}"
        response_coordinates = requests.get(API_URL_COORDS)

        if response_coordinates.status_code != 200:
            st.error("Неверный API-ключ")
        else:
            lat = response_coordinates.json()[0]['lat']
            lon = response_coordinates.json()[0]['lon']
            API_URL_WEATHER = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={input_api_key}"
            response_weather = requests.get(API_URL_WEATHER)
            weather_kelvin = response_weather.json()['main']['temp']
            weather_celsius = from_kelvin_to_celsius(weather_kelvin)
            st.write(f"Текущая погода: {round(weather_celsius, 2)} °C")

            doy = datetime.today().timetuple().tm_yday
            spring = range(80, 172)
            summer = range(172, 264)
            fall = range(264, 355)

            if doy in spring:
                season = 'spring'
            elif doy in summer:
                season = 'summer'
            elif doy in fall:
                season = 'fall'
            else:
                season = 'winter'

            historic_statistics = data_statistics[
                (data_statistics["city"] == input_city) & (data_statistics["season"] == season)]
            historic_mean = round(float(historic_statistics['mean']), 2)
            historic_std = round(float(historic_statistics['std']), 2)

            if weather_celsius > historic_mean + 2 * historic_std or weather_celsius < historic_mean - 2 * historic_std:
                st.write("Текущая температура, по сравнению с историческими данными, не является нормальной")
                st.write(
                    f"Средняя температура в {input_city} в {season}: {historic_mean} °C, отклонение: {historic_std} °C")
            else:
                st.write("Для текущего сезона данная температура нормальна")