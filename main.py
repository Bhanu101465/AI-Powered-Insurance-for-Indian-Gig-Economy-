import pickle 
import contextlib
import joblib 
import pandas as pd

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List 
from contextlib import asynccontextmanager

# FastAPI is a modern python framework for building web apps quickly
"""Pydantic is a Python library that checks whether  data has the 
correct structure and types.
And BaseModel is the main class we use from Pydantic to define that structure."""

"""asynccontextmanager is from Python's contextlib module, and you'll often see 
it in FastAPI for things like starting and shutting down resources."""
"everyhting before yeild is start up part and everything after yeild is end part "
# joblib loads the .pkl files back into python objects 
"pandas bcz every one of the model was trained on a Dataframe with specifc column names  so at prediction time "
"we have to feed it a dataframe with those exact same column names not jsut a list of numbers"

# Model directory + lifespan()

ml = {}
@asynccontextmanager 
async def lifespan(app : FastAPI):
    try :
        ml['risk_model']       = joblib.load('models/risk_profiling_model.pkl')
        ml['premium_rf']       = joblib.load('models/dynamic_premium_model.pkl')
        ml['disruption_model'] = joblib.load('models/disruption_model.pkl')
        ml['fraud_model']      = joblib.load('models/fraud_detection_model.pkl')
        ml['fraud_scaler']     = joblib.load('models/fraud_scaler.pkl')
        ml['risk_map_model']   = joblib.load('models/risk_map_kmeans.pkl')
        ml['risk_map_scaler']  = joblib.load('models/risk_map_scaler.pkl')
        ml['ring_model']       = joblib.load('models/ring_detection_model.pkl')
        ml['ring_scaler']      = joblib.load('models/ring_detection_scaler.pkl')
        zone_df = pd.read_csv('models/zone_risk_map.csv')
        rm_features = ['avg_rainfall_mm','flood_incidents_per_year','avg_aqi',
                       'curfew_days_per_year','hub_closure_days','avg_temp_peak']
        cluster_means = zone_df.groupby('risk_cluster')[rm_features].mean()
        cluster_means['combined_risk'] = (
            cluster_means['avg_rainfall_mm'] / 1500 +
            cluster_means['flood_incidents_per_year'] / 15
        )
        ranking = cluster_means['combined_risk'].rank().astype(int)
        risk_label_map = {ranking.idxmin() : 'Low_Risk',ranking.idxmax() : 'High Risk'}
        for k in [0,1,2] :
            if k not in risk_label_map:
                risk_label_map[k] = 'Medium Risk'
        ml['risk_label_map'] = risk_label_map
    except FileNotFoundError as e :
        print(f"Model file missing : {e}")
        raise 
    yield 
    ml.clear()
"""ml is a python dictionary and this risk_model all are vairables 
we bundle them into one dictionary instead of 9 separate variables bcz if
we dont do like that later we need global_risk_model global for evry model 
we bundle everything into one then we can use only one global
"""
"yield : everything before yield runs once , when the server starts up , "
"everything after yield runs once, when the server shuts down "
# ml ={} instead of nine separate global varibles single ml_model purely to avoid nine 
# global declarations cluttering the function 

app = FastAPI(lifespan = lifespan)
# this line tells the fastapi run the lifespan function around thsi app's start/stop

# helper functions 

def get_fraud_tier(srs) :
    if srs < 0.4 :
        return 'Tier 1 - Auto Approve'
    elif srs < 0.7 :
        return 'Tier 2 - Soft Hold'
    else :
        return 'Tier 3 - Manual Review'

def get_payout_amount(trigger_type):
    payouts = {
        'heavy_rain' : 600 , 'extreme_heat' : 400 , 'severe_aqi' : 350,
        'curfew' : 700 , 'hub_closure' : 500 , 'none' : 0
    }
    return payouts.get(trigger_type , 0) 
# if in payout this data type is no there then return 0 dont crash
"From model3 we get disruption_preidction it goes to def determine trigger then it give "
"smthng like heavy_rain form that this get_payout_amount will give payout 600 rupees "

def determine_triger(disruption_prob , weather_data): # from disruption_prediction_model
    if disruption_prob < 0.5:
        return 'none'
    if weather_data['forecast_rainfall_mm'] > 100:
        return 'heavy_rain'
    elif weather_data['forecast_temp'] > 43:
        return 'extreme_heat'
    elif weather_data['forecast_aqi'] > 280:
        return 'severe_aqi'
    else :
        return 'heavy_rain' # default trigger

#input schema - one class , matching gigshield_pipeline()'s worker_input dict --

# all 6 separate models are fitted into one class bcz gigshield_pipeline() fnc was 
# written to take one combined dictionary and return one combined decision

"Pydantic's job is if someone sends forty instead of 40 for month ,fastapi rejects the request "
"before  code runs with  a clear error "

class WorkerInput(BaseModel):
    worker_id : str
    #zone data 
    avg_rainfall_mm : float
    flood_incidents_per_year : int
    avg_aqi : float
    curfew_days_per_year : int
    hub_closure_days : int
    avg_temp_peak_celsius : float
    worker_density : int
    zone_type : int

    #premium data 
    season : int
    weeks_claim_free : int
    worker_platform : int
# here premium data is using 7 features but those are been typed in before functions and after
#func these reduces the need to type twice 
# in model 2 we have next_week_rain_forecast but we not use dhere but in weather data we used sma eofr other feautes
    #weather data

    current_rainfall_mm : float
    forecast_rainfall_mm : float
    current_temp : float
    forecast_temp : float
    current_aqi : float
    forecast_aqi : float
    wind_speed : float
    humidity : float
    historical_disruption_rate : float
    month : int

    #fraud data

    claim_count_30days : int
    gps_cell_tower_match : int
    inactivity_duration_mins : float 
    timestamp_similarity : float
    delivery_drop_pct : float
    zone_claim_velocity : float
    device_mock_location_flag : int
    avg_claim_interval_days : float

    #ring data 

    claim_timestamp_unix : float
    zone_id_encoded : int
    inactivity_start_time : float
    device_id_hash : int
    referral_chain_depth : int

@app.get("/")
def root():
    return {"status" : "Kavach AI API is running"}


@app.post("/predict")
def predict(worker : WorkerInput):
    w = worker.model_dump()
    # MODEL 1: Risk Profiling
    risk_features = pd.DataFrame([{
        'avg_rainfall_mm': w['avg_rainfall_mm'],
        'flood_incidents_per_year': w['flood_incidents_per_year'],
        'avg_aqi': w['avg_aqi'],
        'curfew_days_per_year': w['curfew_days_per_year'],
        'hub_closure_days': w['hub_closure_days'],
        'avg_temp_peak_celsius': w['avg_temp_peak_celsius'],
        'worker_density': w['worker_density'],
        'zone_type': w['zone_type'],
    }])
    """ in worker input there are so many features but model1 wants only 6 or some features
       so we take it from workerinput only some features """
    zone_risk_score = round(float(ml['risk_model'].predict(risk_features)[0]), 2)
# predict then scikit learn always hands back like this[67.3] we need to take 67.3 from that use [0]
#then rounding of to two integers 
    # MODEL 2: Dynamic Premium
    premium_features = pd.DataFrame([{
        'zone_risk_score': zone_risk_score,
        'season': w['season'],
        'weeks_claim_free': w['weeks_claim_free'],
        'worker_platform': w['worker_platform'],
        'zone_type': w['zone_type'],
        'next_week_rain_forecast': w['forecast_rainfall_mm'],
        'next_week_aqi_forecast': w['forecast_aqi'],
    }])
    weekly_premium = round(float(ml['premium_rf'].predict(premium_features)[0]), 2)
    weekly_premium = max(60, min(100, weekly_premium))

    # MODEL 3: Disruption Prediction
    disruption_features = pd.DataFrame([{
        'current_rainfall_mm': w['current_rainfall_mm'],
        'forecast_rainfall_mm': w['forecast_rainfall_mm'],
        'current_temp': w['current_temp'],
        'forecast_temp': w['forecast_temp'],
        'current_aqi': w['current_aqi'],
        'forecast_aqi': w['forecast_aqi'],
        'wind_speed': w['wind_speed'],
        'humidity': w['humidity'],
        'historical_disruption_rate': w['historical_disruption_rate'],
        'month': w['month'],
    }])
    disruption_prob = round(float(
        ml['disruption_model'].predict_proba(disruption_features)[0][1]), 3)
    disruption_alert = disruption_prob >= 0.5
    trigger_type = determine_triger(disruption_prob, {
        'forecast_rainfall_mm': w['forecast_rainfall_mm'],
        'forecast_temp': w['forecast_temp'],
        'forecast_aqi': w['forecast_aqi'],
    })
    payout_amount = get_payout_amount(trigger_type)

    # MODEL 4: Fraud Detection
    fraud_features = pd.DataFrame([{
        'claim_count_30days': w['claim_count_30days'],
        'gps_cell_tower_match': w['gps_cell_tower_match'],
        'inactivity_duration_mins': w['inactivity_duration_mins'],
        'timestamp_similarity': w['timestamp_similarity'],
        'delivery_drop_pct': w['delivery_drop_pct'],
        'zone_claim_velocity': w['zone_claim_velocity'],
        'device_mock_location_flag': w['device_mock_location_flag'],
        'claim_free_weeks': w['weeks_claim_free'],
        'avg_claim_interval_days': w['avg_claim_interval_days'],
    }])
    fraud_scaled = ml['fraud_scaler'].transform(fraud_features)
    raw_score = ml['fraud_model'].decision_function(fraud_scaled)[0]
    srs = float(1 - (raw_score + 0.5))
    srs = max(0.0, min(1.0, round(srs, 3)))
    fraud_tier = get_fraud_tier(srs)

    # MODEL 5: Dynamic Risk Map
    riskmap_features = pd.DataFrame([{
        'avg_rainfall_mm': w['avg_rainfall_mm'],
        'flood_incidents_per_year': w['flood_incidents_per_year'],
        'avg_aqi': w['avg_aqi'],
        'curfew_days_per_year': w['curfew_days_per_year'],
        'hub_closure_days': w['hub_closure_days'],
        'avg_temp_peak': w['avg_temp_peak_celsius'],
    }])
    riskmap_scaled = ml['risk_map_scaler'].transform(riskmap_features)
    risk_cluster = int(ml['risk_map_model'].predict(riskmap_scaled)[0])
    risk_label = ml['risk_label_map'].get(risk_cluster, 'Medium Risk')

    # MODEL 6: Ring Detection
    # NOTE - see the caveat below the code: this is a known simplification.
    ring_features = pd.DataFrame([{
        'claim_timestamp_unix': w['claim_timestamp_unix'],
        'zone_id_encoded': w['zone_id_encoded'],
        'inactivity_start_time': w['inactivity_start_time'],
        'device_id_hash': w['device_id_hash'],
        'referral_chain_depth': w['referral_chain_depth'],
        'claim_amount': payout_amount if payout_amount > 0 else 500,
    }])
    ring_scaled = ml['ring_scaler'].transform(ring_features)
    ring_cluster = int(ml['ring_model'].fit_predict(ring_scaled)[0])
    ring_membership = 'Genuine - No Ring' if ring_cluster == -1 else f'Fraud Ring {ring_cluster}'

#final decision 
#the order of checks also matters 
    ring_cluster = int(ml['ring_model'].fit_predict(ring_scaled)[0])
    is_ring = ring_cluster != -1
    ring_membership = 'Genuine - No Ring' if not is_ring else f'Fraud Ring {ring_cluster}'
    if not disruption_alert:
        final_decision = 'NO DISRUPTION'
        payout_amount = 0
    elif is_ring:
        final_decision = 'REJECT - Ring Detected'
        payout_amount = 0
    elif fraud_tier == 'TIER 3 - Manual Review' :
        final_decision = 'HOLD - Manual Review'
        payout_amount = 0
    elif fraud_tier == 'TIER 2 - Soft Hold' :
        final_decision = 'SOFT HOLD - Re - verify'
        payout_amount = 0
    else :
        final_decision = 'APPROVE - UPI Payout'
    return { # return everyting of all diffrent model at once 
        'worker_id': w['worker_id'],
        'zone_risk_score': zone_risk_score,
        'weekly_premium': weekly_premium,
        'disruption_prob': disruption_prob,
        'disruption_alert': disruption_alert,
        'trigger_type': trigger_type,
        'spoofing_risk_score': srs,
        'fraud_tier': fraud_tier,
        'risk_label': risk_label,
        'ring_membership': ring_membership,
        'final_decision': final_decision,
        'payout_amount': payout_amount

    }
#here we need requirements.txt file bcz the render has no python packages installed at 
#by this requirement we say install packages
# if the scikit learn version mismatches also it handles it like our scikit learn is non old version
# and render is on newer version we should pin an exact version if we dont say it 
#our model could fail to load or predict incorrently 




