import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import preprocessing
from sklearn.ensemble import RandomForestClassifier

pd.options.mode.chained_assignment = None
train = pd.read_csv("data/train.csv.zip")
test = pd.read_csv("data/test.csv.zip")

train['condition'][train['condition']== "interruption"] = "time pressure"
test['condition'][test['condition']== "interruption"] = "time pressure"

le = preprocessing.LabelEncoder()
le.fit(train['condition'])
train['condition'] = le.transform(train['condition'])
test['condition'] = le.transform(test['condition'])

reduced_train = train[["MEAN_RR", "pNN50", "RMSSD", "SDRR", "HR", "condition"]]

X_train = reduced_train.iloc[:,:-1]
y_train = reduced_train.iloc[:,-1]

X_test = test[X_train.columns]
y_test = test['condition']

model = RandomForestClassifier()
X_train = X_train.values
model.fit(X_train,y_train)

import pickle
pickle.dump(model, open('model.pkl','wb')) 