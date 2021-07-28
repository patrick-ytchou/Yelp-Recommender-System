import pickle
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.utils import shuffle
from datetime import datetime
# from sortedcontainers import SortedList

def load_data():
    """
    Load in the pickle file.
    """
    try:
        with open('data/user2movie.json', 'rb') as f:
            user2movie = pickle.load(f)
        with open('data/movie2user.json', 'rb') as f:
            movie2user = pickle.load(f)
        with open('data/usermovie2rating.json', 'rb') as f:
            usermovie2rating = pickle.load(f)
        with open('data/user2movie_test.json', 'rb') as f:
            user2movie_test = pickle.load(f)
        with open('data/movie2user_test.json', 'rb') as f:
            movie2user_test = pickle.load(f)
        with open('data/usermovie2rating_test.json', 'rb') as f:
            usermovie2rating_test = pickle.load(f)
    except:
        raise Exception('File does not exist.')
    
    return user2movie, movie2user, usermovie2rating, user2movie_test, movie2user_test, usermovie2rating_test

def calculate_coef(K, limit, user2movie, movie2user, movie2user_test):
    """
    Conduct modeling.
    
    Parameters
    --------
    K: int, number of neighbors to consider for correlation calculation
    limit: int, least number of common movies users mush have in common in order to consider
    """
    N = np.max(list(user2movie.keys())) + 1
    m1 = np.max(list(movie2user.keys()))
    m2 = np.max(list(movie2user_test.keys()))
    M = max(m1, m2) + 1 ## we might find another unseen movie id in test set.
    
    neighbors = [] # store neighbors in this list 
    averages = [] # each user's average rating
    deviations = [] # each user's deviation
    i = 0
    print("Total users: ", N)
    for i in range(N):
        print("Now processing: user ", i)
        # find K closest users to user i 
        movies_i = user2movie[i]
        movies_i_set = set(movies_i)
        
        # calculate avg and deviation
        rating_i = {movie: usermovie2rating[(i, movie)] for movie in movies_i_set}
        avg_i = np.mean(list(rating_i.values()))
        dev_i = {movie: (rating - avg_i) for movie, rating in rating_i.items()}
        dev_i_values = np.array(list(dev_i.values()))
        sigma_i = np.sqrt(dev_i_values.dot(dev_i_values))
        
        # save results
        averages.append(avg_i)
        deviations.append(dev_i)
        
        # loop through all other users to look for similar ones
        sl = []
        for j in range(N):
            if j != i:
                movies_j = user2movie[j]
                movies_j_set = set(movies_j)
                common_movies = (movies_i_set & movies_j_set) # intersection
                
                if len(common_movies) > limit:
                    # calculate avg and deviation
                    rating_j = {movie: usermovie2rating[(j, movie)] for movie in movies_j}
                    avg_j = np.mean(list(rating_j.values()))
                    dev_j = {movie: (rating - avg_j) for movie, rating in rating_j.items()}
                    dev_j_values = np.array(list(dev_j.values()))
                    sigma_j = np.sqrt(dev_j_values.dot(dev_j_values))
                    
                    # calculate correlation coefficient
                    numerator = sum(dev_i[m]*dev_j[m] for m in common_movies)
                    w_ij = numerator / (sigma_i * sigma_j)
                    
                    # truncate if there are too many values in the sorted list
                    # sl.add((-w_ij,j)) # store negative weight because the list is sorted ascending
                    sl.append((-w_ij, j))
                    sl = sorted(sl)
                    if len(sl) > K:
                        del sl[-1]
    # store the neighbors
    neighbors.append(sl)
    return sl, neighbors, averages, deviations
 
def _predict(i, m, sl, neighbors, averages, deviations):
    """
    Helper function to make prediction for user i on movie m based on pre-computed coef.
    
    Parameters
    --------
    i: int, index for user 
    m: int, index for movie
    sl: sorted list
    neighbors: 
    averages: 
    deviations: 
    """
    numerator, denominator = 0, 0
    for neg_w, j in neighbors[i]:
        try:
            # note that we store negative weights
            numerator += -neg_w * deviations[j][m]
            denominator += abs(-neg_w)
        except KeyError: # if the movie does not exist
            pass
    
    if denominator == 0:
        prediction = averages[i]
    else:
        prediction = numerator / denominator + averages[i]
        
    # clip the prediction to [0.5, 5]
    prediction = max(min(5, prediction), 0.5)
    return prediction

def predict(usermovie2rating, usermovie2rating_test, sl, neighbors, averages, deviations):
    """
    Make prediction for all the ratings.
    """
    train_predictions = []
    train_targets = []
    print("Now: Loop through training dataset.")
    i = 0 
    for (i, m), target in usermovie2rating.items():
        print("Now predicting (train): user ", i)
        # predict for each of the user movie rating entry
        prediction = _predict(i, m, sl, neighbors, averages, deviations)
        
        train_predictions.append(prediction)
        train_targets.append(target)
        i += 1
    
    print("Now: Loop through testing dataset.")
    test_predictions = []
    test_targets = []
    i = 0
    for (i, m), target in test_predictions.items():
        print("Now predicting (test): user ", i)
        prediction = _predict(i, m, sl, neighbors, averages, deviations)
        test_predictions.append(prediction)
        test_targets.append(target)
        i += 1

    return train_predictions, train_targets, test_predictions, test_targets

def calculate_rmse(prediction ,target):
    """
    Calculate mean squared error
    
    Parameters
    --------
    """
    p = np.array(prediction)
    t = np.array(target)
    return np.sqrt(np.mean((p-t)**2))
                
if __name__ == '__main__':
    print("Now: Load data.")
    user2movie, movie2user, usermovie2rating, user2movie_test, movie2user_test, usermovie2rating_test = load_data()
    print("Now: Calculate coefficient values.")
    K = 25
    limit = 5
    sl, neighbors, averages, deviations = calculate_coef(K, limit, user2movie, movie2user, movie2user_test)
    print("Now: Perform Collaborative Filtering.")
    train_predictions, train_targets, test_predictions, test_targets = predict(usermovie2rating, usermovie2rating_test, sl, neighbors, averages, deviations)
    print('Train rmse: ', calculate_rmse(train_predictions, train_targets))
    print('Test rmse: ', calculate_rmse(test_predictions, test_targets))