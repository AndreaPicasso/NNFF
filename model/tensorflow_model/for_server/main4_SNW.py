
import pandas as pd
import numpy as np
import tensorflow as tf
import math
from datetime import datetime, timedelta
from sklearn import preprocessing
from sklearn.metrics import confusion_matrix
from math import sqrt
import matplotlib.pyplot as plt

#tf.logging.set_verbosity(tf.logging.INFO)



skip_vector_dim = 7
n_y = 1 #Numero di output, Per ora sali / scendi poi metteremo neutrale



def sign(x):
    if x >= 0:
        return 1
    elif x < 0:
        #return -1
        return 0
    
class Data():
    X = []
    Y = []


    def get_train_test_set(test_percentage=0.3):
        idx_split = math.floor(len(Data.X)*(1-test_percentage))

        train_x = Data.X[:idx_split]
        train_y = Data.Y[:idx_split]
        test_x = Data.X[idx_split:]
        test_y = Data.Y[idx_split:]

        return (train_x, train_y), (test_x, test_y)



    def get_cross_validation_train_dev_set(test_percentage=0.3, k_fold = 10,  dev_num_points=100):

        # https://stats.stackexchange.com/questions/14099/using-k-fold-cross-validation-for-time-series-model-selection/14109#14109


        # fold = list(train_i , dev_i)
        # train_i = (train_x, train_y) 
        (train_x, train_y), _  = Data.get_train_test_set(test_percentage=test_percentage)
        m = int(len(train_x))
        samples_per_fold = int( (m - dev_num_points) / k_fold)
        # print('Fold lenght: '+str(samples_per_fold))
        fold = list()
        index = 0
        while(len(fold) < k_fold):
            fold.append(((train_x[index:index+samples_per_fold], train_y[index:index+samples_per_fold]),
                    (train_x[index+samples_per_fold:index+samples_per_fold+dev_num_points], train_y[index+samples_per_fold:index+samples_per_fold+dev_num_points])))
            index += samples_per_fold

        return fold





    def load_data(ticker='AAPL', momentum_window=30, newsTimeToMarket = 0, set_verbosity=True):
        X_path = 'SentimentSingleNewsFullNoNorm/'+str(ticker)+'.csv'
        Y_path = 'DataSetIndexes/indexes'+str(ticker)+'.csv'
        
        
        
        if(set_verbosity):
            print('Reading dataset...')
            
        x = pd.read_csv(X_path)
        x = x.rename(index=str, columns={"initTime": "PUBLICATION_DATE"})
        #cambio l'ordine dalla piu vecchia alla piu recente
        if(set_verbosity):
            print('Ordering dataset...')
        x = x.sort_values(by=['PUBLICATION_DATE'])
        x = x.reset_index(drop=True)
        

            

        for i, row in x.iterrows():
            x.at[i,'PUBLICATION_DATE'] =datetime.strptime(x['PUBLICATION_DATE'][i], '%Y-%m-%d %H:%M:%S') + timedelta(hours=newsTimeToMarket)

            
            
            
        y = pd.read_csv(Y_path)
        y = y.rename(index=str, columns={"Unnamed: 0": "DATE"})

        #PER ORA SCARTO GLI INDICI, POI SARA' DA METTERLI DENTRO X
        #y = y['DATE', 'close']
        for i, row in y.iterrows():
            y['DATE'].at[i] = datetime.strptime(y['DATE'][i], '%Y-%m-%d %H:%M:%S') 

        z = list()
        if(set_verbosity):
            print('y(t) - y(t-1) ...')
        #PAST
        for i in range(momentum_window,y.shape[0]):
            z.append((y['close'][i] - y['close'][i-momentum_window])/y['close'][i-momentum_window])

        y = y.reset_index(drop=True)
        y.drop(np.arange(0, momentum_window), inplace=True)
        y = y.reset_index(drop=True)
        y['close'] = [sign(entry) for entry in z]
        y = y.reset_index(drop=True)

        # if(set_verbosity):
        #     plt.figure(figsize=(20,10))
        #     plt.plot(np.arange(0, len(x)), x['CONSTRAINING'],'b')
        #     plt.plot(np.arange(0, len(x)), x['LITIGIOUS'],'g')
        #     plt.plot(np.arange(0, len(x)), x['NEGATIVE'],'m')
        #     plt.plot(np.arange(0, len(x)), x['POSITIVE'],'c')
        #     plt.plot(np.arange(0, len(x)), x['UNCERTAINTY'],'k')
        #     plt.ylabel('INPUT')
        #     plt.xlabel('time')
        #     plt.show()


        #Normalizzo
        min_max_scaler = preprocessing.MinMaxScaler()
        x[['CONSTRAINING', 'LITIGIOUS','NEGATIVE','POSITIVE','UNCERTAINTY', 'SUPERFLUOUS','INTERESTING']] = min_max_scaler.fit_transform(x[['CONSTRAINING', 'LITIGIOUS','NEGATIVE','POSITIVE','UNCERTAINTY','SUPERFLUOUS','INTERESTING']].values)
        
        
        if(set_verbosity):
            print('Alligning dataset and constructing cube..')

        initDate = max(y['DATE'][0], x['PUBLICATION_DATE'][0])
        finalDate = min(y['DATE'][len(y)-1], x['PUBLICATION_DATE'][len(x)-1])
        i = 0
        j = 0

        # ALLINEAMENTO INIZIO
        while(y['DATE'][j] < initDate):
            j+=1
        while(x['PUBLICATION_DATE'][i] < initDate):
            i+=1

        y.drop(np.arange(0, j), inplace=True)
        y = y.reset_index(drop=True)
        x.drop(np.arange(0, i), inplace=True)
        x = x.reset_index(drop=True)
        i = 0
        j = 0

        numTimeSteps = sum([1 if(y['DATE'][j] > initDate and y['DATE'][j]<finalDate) else 0 for j in range(len(y))])
        numNews = sum([1 if(x['PUBLICATION_DATE'][i] > initDate and x['PUBLICATION_DATE'][i]<finalDate) else 0 for i in range(len(x))]) 

        X = list()
        # M = np.zeros(shape=(numNews,numTimeSteps))  # boolean mask: Mij = X[time][i] < Y[time][j]
        Y = list()
        Z = list()


        currentDate = initDate
        while(y['DATE'][j] < finalDate ):
            Y.append(y['close'][j])
            Z.append(z[j])
            temp = x[x['PUBLICATION_DATE'] < y['DATE'][j]]
            temp = temp[temp['PUBLICATION_DATE'] > y['DATE'][j] - timedelta(days=4)]
            timeSlotX = [temp['CONSTRAINING'].tolist(),temp['LITIGIOUS'].tolist(),temp['NEGATIVE'].tolist(),temp['POSITIVE'].tolist(),temp['UNCERTAINTY'].tolist(),temp['SUPERFLUOUS'].tolist(),temp['INTERESTING'].tolist()]
            timeSlotX = np.asarray(timeSlotX).transpose().tolist()
            X.append(timeSlotX)
            j+=1

        maxNewsPerHour = 0
        for i in range(len(X)):
            if(len(X[i])>maxNewsPerHour):
                maxNewsPerHour = len(X[i])
        for i in range(len(X)):
            
            while(len(X[i])<maxNewsPerHour):
                X[i].append([0]*skip_vector_dim)


        Data.X = np.asarray(X)
        Data.Y = np.asarray(Y)



class MyModel():
    
    def __init__(self, num_lstm_units, num_lstm_layers, news_per_hour, learning_rate = 0.009,
              num_epochs = 30, minibatch_size = 128,):
        self.num_lstm_units = num_lstm_units
        self.num_lstm_layers = num_lstm_layers
        self.news_per_hour = news_per_hour
        self.learning_rate = learning_rate
        self.num_epochs = num_epochs
        self.minibatch_size = minibatch_size
        
        

    ## Managing state through batches:
    def get_state_variables(self, state_placeholder):
        l = tf.unstack(state_placeholder, axis=0)
        rnn_tuple_state = tuple(
        [tf.nn.rnn_cell.LSTMStateTuple(l[idx][0], l[idx][1])
         for idx in range(self.num_lstm_layers)]
        )
        return rnn_tuple_state

    def get_initial_state(self):
        if(self.num_lstm_layers == 1):
            return np.zeros([self.num_lstm_layers, 2, 1, self.num_lstm_units])

        return tuple([tf.nn.rnn_cell.LSTMStateTuple(np.zeros([1, 1, self.num_lstm_units]), np.zeros([1, 1, self.num_lstm_units]))for idx in range(self.num_lstm_layers)])



    def create_placeholders(self):
        X = tf.placeholder(tf.float32, shape=(None, self.news_per_hour, skip_vector_dim), name='X')
        Y = tf.placeholder(tf.float32, shape=(None, n_y), name='Y')
        lstm_state_placeholder = tf.placeholder(tf.float32, [self.num_lstm_layers, 2, None, self.num_lstm_units],  name='lstm_state')
        
        return X, Y, lstm_state_placeholder



    def forward_propagation(self, X, init_state = None):

        if init_state != None:
            init_state = self.get_state_variables(init_state)

        # ATTENTION
        e = tf.layers.dense(inputs=X, units=1, activation=tf.nn.relu)
        alpha = tf.nn.softmax(e, name='attention_weights')                                                  # tf.nn.softmax(logits,axis=None, ..)
        timeSlotEmbeddings =  tf.matmul(alpha, X, transpose_a=True, name='timeSlotEmbeddings')              # tf.matmul(a,b, transpose_a=False, transpose_b=False, name=None )

        # # LSTM
        # # (see https://jasdeep06.github.io/posts/Understanding-LSTM-in-Tensorflow-MNIST/)

        timeSlotSequence = timeSlotEmbeddings                                                           # 1 sequenza di ? sample timeSlotEmbeddings.shape = (?, 1, 2400) -> memoria tra i vari sample


        # VEDERE COME FUNZIONA BACKPROP THROUGH TIME PER VEDERE QUALE E MEGLIO
        #timeSlotSequence = tf.transpose(timeSlotEmbeddings, perm=[1, 0, 2])                                # ? sequenze di 1 sample -> NON c'e memoria esplicita tra i vari sample

        #lstm_layer = tf.contrib.rnn.BasicLSTMCell(num_lstm_units)                                          # Definisco il layer
        lstm_layer = tf.contrib.rnn.LSTMCell(self.num_lstm_units, use_peepholes=True)                       # Definisco il layer

        lstm_network = tf.contrib.rnn.MultiRNNCell([lstm_layer] * self.num_lstm_layers)


        outputs, new_states = tf.nn.dynamic_rnn(lstm_network, timeSlotSequence,
             initial_state=init_state,  dtype="float32",time_major=True)                                    # Definisco la rete ricorrente tramite il layer precedente


        outputs = tf.squeeze(outputs, axis=1)
    #       outputs = tf.squeeze(outputs, axis=0)

        prediction = tf.layers.dense(outputs, 1, activation=tf.nn.sigmoid)


        return prediction, new_states



    def compute_cost(self, Y_hat, Y):
        cost = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits = Y_hat, labels = Y))      # Y * -log(sigmoid(Y_hat)) + (1 - Y) * -log(1 - sigmoid(Y_hat))
        #cost = tf.reduce_mean(tf.squared_difference(Y_hat, Y))
        return cost



    def mini_batches(self, X_train, Y_train):
        minibatches = list()

        m = int(len(X_train))
        if(self.minibatch_size > m):
            minibatches.append((X_train, Y_train))
            return minibatches

        minibatches.append((X_train[0:self.minibatch_size], Y_train[0:self.minibatch_size]))
        iterSize = self.minibatch_size
        while(iterSize < m):
            if(iterSize+self.minibatch_size < m):
                minibatches.append((X_train[iterSize:iterSize+self.minibatch_size], Y_train[iterSize:iterSize+self.minibatch_size]))
                iterSize += self.minibatch_size
            else:
                minibatches.append((X_train[iterSize:m],Y_train[iterSize:m]))
                iterSize = m
        return minibatches


    def runWithEarlyStopping(self, X_train, Y_train, X_dev, Y_dev, X_test=None, Y_test=None, set_verbosity=True):

        tf.reset_default_graph()                                                            # to be able to rerun the model without overwriting tf variables
        m =int(len(X_train))
        costs_train = []
        costs_dev = []
        accuracy_train = []
        accuracy_dev = []
        yhat_each_epoch = []
        MCCs_dev = []
        # Create Placeholders of the correct shape
        X, Y, lstm_state_placeholder = self.create_placeholders()

        # Forward propagation: Build the forward propagation in the tensorflow graph
        prediction, lstm_next_state = self.forward_propagation(X, lstm_state_placeholder)

        # Cost function: Add cost function to tensorflow graph
        cost = self.compute_cost(prediction, Y)
        #cost = self.compute_cost(prediction, Y)

        # Backpropagation: Define the tensorflow optimizer. Use an AdamOptimizer that minimizes the cost.
        optimizer = tf.train.AdamOptimizer(learning_rate = self.learning_rate).minimize(cost)
        #grads = tf.train.AdamOptimizer(learning_rate = learning_rate).compute_gradients(cost)

        # Initialize all the variables globally
        init = tf.global_variables_initializer()

        #This is for computing the test accuracy every epoch
        predict_op = tf.to_float(prediction > 0.5)

        correct_prediction = tf.equal(predict_op, Y)
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))


        # Start the session to compute the tensorflow graph
        with tf.Session() as sess:
            sess.run(init)


          # Do the training loop
            for epoch in range(self.num_epochs):
                # 1 perche per ora ho 1 sola sequenza
                lstm_state = self.get_initial_state()
                #lstm_state = np.zeros([num_lstm_layers, 2, 1, num_lstm_units])                                                     #Ogni epoch reinizializzo stato

                minibatch_cost = 0.0
                num_minibatches = int(m / self.minibatch_size)
                if(num_minibatches == 0):
                    num_minibatches = 1
                minibatches = self.mini_batches(X_train, Y_train)


                for minibatch in minibatches:
                    # Select a minibatch
                    (minibatch_X, minibatch_Y) = minibatch
                    minibatch_X = np.asarray(minibatch_X)
                    minibatch_Y = np.asarray(minibatch_Y).reshape((len(minibatch_Y), 1))

                    # Run the session to execute the optimizer and the cost, the feedict should contain a minibatch for (X,Y).
                    _ , temp_cost, lstm_state = sess.run([optimizer, cost, lstm_next_state], feed_dict={X: minibatch_X, Y: minibatch_Y, lstm_state_placeholder: lstm_state})
                    # weights = tf.get_default_graph().get_tensor_by_name('dense_1/kernel:0')
                    #print('state: ' +str(new_state))
                    minibatch_cost += temp_cost / num_minibatches
                # Print the cost every epoch
                if  epoch % 1 == 0:
                    lstm_temp_state = self.get_initial_state()
                    trainCost, lstm_temp_state = sess.run([cost, lstm_next_state], feed_dict={X: np.asarray(X_train), Y: np.asarray(Y_train).reshape((len(Y_train), 1)), lstm_state_placeholder: lstm_temp_state})
                    costs_train.append(trainCost)
                    devCost = sess.run(cost, feed_dict={X: np.asarray(X_dev), Y: np.asarray(Y_dev).reshape((len(Y_dev), 1)), lstm_state_placeholder: lstm_temp_state})
                    costs_dev.append(devCost)

                    lstm_temp_state  = self.get_initial_state()
                    trainAccuracy, lstm_temp_state = sess.run([accuracy, lstm_next_state], feed_dict={X: np.asarray(X_train), Y: np.asarray(Y_train).reshape((len(Y_train), 1)),lstm_state_placeholder: lstm_temp_state})
                    devAccuracy = sess.run(accuracy, feed_dict={X: np.asarray(X_dev), Y: np.asarray(Y_dev).reshape((len(Y_dev), 1)),lstm_state_placeholder: lstm_temp_state})
                    yhat = sess.run(prediction, feed_dict={X: np.asarray(X_dev), Y: np.asarray(Y_dev).reshape((len(Y_dev), 1)),lstm_state_placeholder: lstm_temp_state})

                    yhat = [sign(x-0.5) for x in yhat]  
                    yhat_each_epoch.append(yhat)
                    cm = confusion_matrix(Y_dev, yhat)
                    tn, fp, fn, tp = cm.ravel()
                    denom = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
                    MCCs_dev.append(0 if denom== 0 else (tp*tn -fp*fn)/sqrt(denom) )

                    accuracy_train.append(float(trainAccuracy))
                    accuracy_dev.append(float(devAccuracy))

                if  set_verbosity and epoch % 5 == 0:
                    #print('miniCost ='+str(minibatch_cost))
                    print("Epoch "+str(epoch)+": \tTrain cost: "+str(trainCost)+" \tDev cost: "+str(devCost)+" \tTrain Accuracy: "+str(trainAccuracy)+" \tDev accuracy: "+str(devAccuracy))

        # plt.figure(figsize=(20,10))
        # plt.plot(range(0,len(MCCs_dev)),MCCs_dev,'--r', label='MCCs_dev' )
        # plt.ylabel('accuracy')
        # plt.xlabel('epochs')
        # plt.title("MCC ")
        # plt.legend()
        # plt.show() 

        if(type(X_test) != type(None) and type(Y_test) != type(None)):

            costs_train = []
            costs_test = []
            accuracy_train = []
            accuracy_test = []
            yhat_each_epoch = []
            #Retrain untill the optimal num_epochs accuracy on the dev
            with tf.Session() as sess:
                sess.run(init)
                accuracy_dev = np.convolve(accuracy_dev, np.ones((4,))/4, mode='same') #Stop when the accuracy on the dev is maximum, apply a moving average of W=4 to avoid peeks
                for epoch in range(np.argmax(accuracy_dev)+1):
                    lstm_state = self.get_initial_state()
                    minibatch_cost = 0.0
                    num_minibatches = int(m / self.minibatch_size)
                    if(num_minibatches == 0):
                        num_minibatches = 1
                    minibatches = self.mini_batches(X_train, Y_train)
                    for minibatch in minibatches:
                        (minibatch_X, minibatch_Y) = minibatch
                        minibatch_X = np.asarray(minibatch_X)
                        minibatch_Y = np.asarray(minibatch_Y).reshape((len(minibatch_Y), 1))
                        _ , temp_cost, lstm_state = sess.run([optimizer, cost, lstm_next_state], feed_dict={X: minibatch_X, Y: minibatch_Y, lstm_state_placeholder: lstm_state})
                        minibatch_cost += temp_cost / num_minibatches
 

                    lstm_temp_state = self.get_initial_state()
                    trainCost, lstm_temp_state = sess.run([cost, lstm_next_state], feed_dict={X: np.asarray(X_train), Y: np.asarray(Y_train).reshape((len(Y_train), 1)), lstm_state_placeholder: lstm_temp_state})
                    costs_train.append(trainCost)
                    testCost = sess.run(cost, feed_dict={X: np.asarray(X_test), Y: np.asarray(Y_test).reshape((len(Y_test), 1)), lstm_state_placeholder: lstm_temp_state})
                    costs_test.append(testCost)

                    lstm_temp_state  = self.get_initial_state()
                    trainAccuracy, lstm_temp_state = sess.run([accuracy, lstm_next_state], feed_dict={X: np.asarray(X_train), Y: np.asarray(Y_train).reshape((len(Y_train), 1)),lstm_state_placeholder: lstm_temp_state})
                    accuracy_train.append(float(trainAccuracy))
                    testAccuracy = sess.run(accuracy, feed_dict={X: np.asarray(X_test), Y: np.asarray(Y_test).reshape((len(Y_test), 1)),lstm_state_placeholder: lstm_temp_state})
                    accuracy_test.append(float(testAccuracy))
                    yhat = sess.run(prediction, feed_dict={X: np.asarray(X_test), Y: np.asarray(Y_test).reshape((len(Y_test), 1)),lstm_state_placeholder: lstm_temp_state})
                    yhat_each_epoch.append(yhat)

                    if  set_verbosity and epoch % 5 == 0:
                        print('miniCost ='+str(minibatch_cost))
                        print("Epoch "+str(epoch)+": \tTrain cost: "+str(trainCost)+" \tTest cost: "+str(testCost)+" \tTrain Accuracy: "+str(trainAccuracy)+" \tTest accuracy: "+str(testAccuracy))

                if(set_verbosity):
                    # plt.figure(figsize=(20,10))
                    # plt.plot(range(0,len(accuracy_train)), accuracy_train,'b', label='accuracy_train')
                    # plt.plot(range(0,len(accuracy_test)), accuracy_test,'r', label='accuracy_test')
                    # plt.plot(range(0,len(costs_train)),costs_train,'--b', label='cost_train')
                    # plt.plot(range(0,len(costs_test)),costs_test,'--r', label='cost_test' )

                    # plt.ylabel('accuracy')
                    # plt.xlabel('epochs')
                    # plt.title("Learning rate =" + str(self.learning_rate))
                    # plt.legend()
                    # plt.show()
                    print("Train Accuracy:", accuracy_train[-1])
                    print("Test Accuracy:",  accuracy_test[-1])
                return (accuracy_train, accuracy_test), yhat_each_epoch
            
        else:
            if(set_verbosity):
                # plt.figure(figsize=(20,10))
                # plt.plot(range(0,len(accuracy_train)), accuracy_train,'b', label='accuracy_train')
                # plt.plot(range(0,len(accuracy_dev)), accuracy_dev,'r', label='accuracy_test')
                # plt.plot(range(0,len(costs_train)),costs_train,'--b', label='cost_train')
                # plt.plot(range(0,len(costs_dev)),costs_dev,'--r', label='cost_test' )

                # plt.ylabel('accuracy')
                # plt.xlabel('epochs')
                # plt.title("Learning rate =" + str(self.learning_rate))
                # plt.legend()
                # plt.show()
                print("Train Accuracy:", max(accuracy_train))
                print("Dev Accuracy:",  max(accuracy_dev))

            return (accuracy_train, accuracy_dev), yhat_each_epoch


class ModelSelection():
        

    def modelSelectionFixedTTM(ticker='AAPL', iterations = 20, learning_rate = 0.001, minibatch_size = 512):
        import os
        # fold = list(train_i , dev_i)
        # train_i = (train_x, train_y) 
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        print('\n\n\n==================== '+str(ticker)+' ==================== \n\n\n')

        best_NumLSTMUnits = []
        
        Ttm_range = [0, 7, 14, 21, 35, 70, 105, 210]
        bestAccuracy = 0
        # Each day: 7 hours of trading
        for newsTimeToMarketIndex in range(0, len(Ttm_range)):
            newsTimeToMarket = Ttm_range[newsTimeToMarketIndex]
            print('\n'+str(newsTimeToMarket), end="", flush=True)
            
            best_NumLSTMUnits.append(0)
            
            for i in range(0,iterations):
                numLSTMUnits = np.asscalar(np.random.random_integers(200, 500))


                Data.load_data(ticker= ticker,momentum_window=30, newsTimeToMarket = newsTimeToMarket, set_verbosity=False)

                folds = Data.get_cross_validation_train_dev_set(test_percentage=0.3, k_fold = 3,  dev_num_points=100)
            
                k_fold_train_accuracy = []
                k_fold_dev_accuracy = []
                for fold in folds:
                    print("=", end="", flush=True)
                    (X_train, Y_train), (X_dev, Y_dev) = fold

                    model = MyModel(num_lstm_units=numLSTMUnits, num_lstm_layers=1, news_per_hour = X_train.shape[1],
                                learning_rate = learning_rate, num_epochs = 35, minibatch_size = minibatch_size)
                
                    (train_accuracy, dev_accuracy), _ = model.runWithEarlyStopping(X_train,Y_train,X_dev,Y_dev, set_verbosity=False)
                    #To select the best hyperparams, rely on the best accuracy achived with the dev (OPT early stopping), but in order to remove noise apply a win avg on the epochs and use the cross validation
                    train_accuracy = max(np.convolve(train_accuracy, np.ones((4,))/4, mode='same'))
                    dev_accuracy = max(np.convolve(dev_accuracy, np.ones((4,))/4, mode='same'))
                    k_fold_train_accuracy.append(train_accuracy)
                    k_fold_dev_accuracy.append(dev_accuracy)
#                 print('( train_fold_accuracy: '+str(sum(k_fold_train_accuracy) / len(folds))+ ', dev_fold_accuracy: '+str(sum(k_fold_dev_accuracy) / len(folds))+' )')
#                 print('( train_fold_variance: '+str(np.var(np.asarray(k_fold_train_accuracy)))+ ', dev_fold_variance: '+str(np.var(np.asarray(k_fold_dev_accuracy)))+' )')
            dev_accuracy = np.mean(k_fold_dev_accuracy)
            if(dev_accuracy > bestAccuracy):
                best_NumLSTMUnits[newsTimeToMarketIndex] = numLSTMUnits
                

        print('\n#################################\n')
        print('BEST:')
        print('Predicting the future at: '+str(np.asarray(Ttm_range)/7)+' days')
        print('best_NumLSTMUnits: '+str(best_NumLSTMUnits))
        print('\n#################################\n')
                    
        print('Training optimal model...')
        train_accs = []
        test_accs = []
        MCCs = []
        MCCsReal = []
        TP = []
        TN = []
        FP = []
        FN = []
        always_yes = []
        for newsTimeToMarketIndex in range(0, len(Ttm_range)):
            newsTimeToMarket = Ttm_range[newsTimeToMarketIndex]
            Data.load_data(ticker= ticker,momentum_window=30, newsTimeToMarket = newsTimeToMarket, set_verbosity=False)
            
            _ , (X_test, Y_test) = Data.get_train_test_set()
            #For training I take the biggest fold, validation on dev for early stopping (opt num epochs)
            folds = Data.get_cross_validation_train_dev_set(test_percentage=0.3, k_fold = 3,  dev_num_points=100)
            (X_train, Y_train), (X_dev, Y_dev) = folds[-1] 

            #(X_train, Y_train) , (X_test, Y_test) = Data.get_train_test_set()
            
            model = MyModel(num_lstm_units=best_NumLSTMUnits[newsTimeToMarketIndex], num_lstm_layers=1,
                            news_per_hour = X_train.shape[1],learning_rate = learning_rate,
                            num_epochs = 35, minibatch_size = minibatch_size)
                
            
            #(train_accuracy, test_accuracy), yhat_each_epoch = model.run(X_train,Y_train, X_test, Y_test)
            (train_accuracy, test_accuracy), yhat_each_epoch = model.runWithEarlyStopping(X_train, Y_train, X_dev, Y_dev, X_test, Y_test)

            
            yhat = [sign(x-0.5) for x in yhat_each_epoch[-1]]  
            cm = confusion_matrix(Y_test, yhat)
            tn, fp, fn, tp = cm.ravel()
            denom = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
            MCCsReal.append(0 if denom== 0 else (tp*tn -fp*fn)/sqrt(denom) )
            TP.append(tp)
            TN.append(tn)
            FN.append(fn)
            FP.append(fp)

            if(tp + fp == 0):
                tp = 1
            if(tp + fn == 0):
                tp = 1
            if(tn + fp == 0):
                tn = 1
            if(tn + fn == 0):
                tn = 1

            train_accs.append(train_accuracy[-1])
            test_accs.append(test_accuracy[-1])
            MCCs.append((tp*tn -fp*fn)/sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))
            b = [1 if (Y_test[i]==1) else 0 for i in range(len(Y_test))  ]
            tot = np.sum(np.asarray(Y_test))
            b = np.sum(np.asarray(b))/tot
            b = 1-b if(b<0.5) else b
            always_yes.append(b)
            # plt.figure(figsize=(20,10))
            # plt.plot(range(0,len(Y_test)), yhat_each_epoch[np.argmax(test_accuracy)],'c', label='yhat_OPT') #Prediction with best accuracy
            # plt.plot(range(0,len(Y_test)), yhat_each_epoch[-1],'b', label='yhat') #Prediction with best accuracy

            # plt.plot(range(0,len(Y_test)), Y_test,'r', label='y')
            # plt.legend()
            # plt.show()
            # plt.savefig('Predictions/'+ticker+'.png')


        print(ticker)
        print('Ttm_range, '+str(Ttm_range))
        print('y=1,'+str(ticker)+', '+str(always_yes))
        print('test,'+str(ticker)+', '+str(test_accs))
        print('MCC,'+str(ticker)+', '+str(MCCs))
        print('MCC_R,'+str(ticker)+', '+str(MCCsReal))
        print('TN,'+str(ticker)+', '+str(TN))
        print('FP,'+str(ticker)+', '+str(FP))
        print('FN,'+str(ticker)+', '+str(FN))
        print('TP,'+str(ticker)+', '+str(TP))

        



# tickers = ['AAPL','AMZN','GOOGL','MSFT','FB','INTC','CSCO','CMCSA','NVDA','NFLX']       
# for tic in tickers:
#     ModelSelection.modelSelectionFixedTTM(ticker=tic, iterations = 10, learning_rate = 0.001, minibatch_size = 512)



# SINGLE RUN
learning_rate=0.001
batch_size=512


num_lstm_layers = 1
num_lstm_units = 470
newsTimeToMarket = 0


tickers = ['AAPL','AMZN','GOOGL','MSFT','FB','INTC','CSCO','CMCSA','NVDA','NFLX']       
for ticker in tickers:
# ticker='AAPL'
    print('\n\n\n==================== '+str(ticker)+' ==================== \n\n\n')
    train_accs = []
    test_accs = []
    MCCs = []
    MCCsReal = []
    TP = []
    TN = []
    FP = []
    FN = []
    always_yes = []


    Ttm_range = [0, 7, 14, 21, 28, 35, 70, 105, 210]
    # Each day: 7 hours of trading
    for newsTimeToMarket in Ttm_range:
        Data.load_data(ticker=ticker,
                       momentum_window=30,
                       newsTimeToMarket = newsTimeToMarket,set_verbosity=False)

        (X_train, Y_train), (X_test, Y_test) = Data.get_train_test_set()

        test_x = tf.convert_to_tensor(np.asarray(X_test), dtype=tf.float32)
        train_x = tf.convert_to_tensor(np.asarray(X_train), dtype=tf.float32)

        train_y = tf.convert_to_tensor(np.asarray(Y_train), dtype=tf.float32)
        test_y = tf.convert_to_tensor(np.asarray(Y_test), dtype=tf.float32)


        model = MyModel(num_lstm_units=num_lstm_units, num_lstm_layers=num_lstm_layers, news_per_hour = train_x.shape[1],
                        learning_rate = learning_rate, num_epochs = 35, minibatch_size = batch_size)

        (train_accuracy, test_accuracy), yhat_each_epoch = model.runWithEarlyStopping(X_train, Y_train, X_test, Y_test)

        yhat = [sign(x-0.5) for x in yhat_each_epoch[-1]]  
        cm = confusion_matrix(Y_test, yhat)
        tn, fp, fn, tp = cm.ravel()
        denom = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
        MCCsReal.append(0 if denom== 0 else (tp*tn -fp*fn)/sqrt(denom) )
        TP.append(tp)
        TN.append(tn)
        FN.append(fn)
        FP.append(fp)

        if(tp + fp == 0):
            tp = 1
        if(tp + fn == 0):
            tp = 1
        if(tn + fp == 0):
            tn = 1
        if(tn + fn == 0):
            tn = 1

        train_accs.append(train_accuracy[-1])
        test_accs.append(test_accuracy[-1])
        MCCs.append((tp*tn -fp*fn)/sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))
        b = [1 if (Y_test[i]==1) else 0 for i in range(len(Y_test))  ]
        tot = np.sum(np.asarray(Y_test))
        b = np.sum(np.asarray(b))/tot
        b = 1-b if(b<0.5) else b
        always_yes.append(b)


    print(ticker)
    print('Ttm_range, '+str(Ttm_range))
    print('y=1,'+str(ticker)+', '+str(always_yes))
    print('test,'+str(ticker)+', '+str(test_accs))
    print('MCC,'+str(ticker)+', '+str(MCCs))
    print('MCC_R,'+str(ticker)+', '+str(MCCsReal))
    print('TN,'+str(ticker)+', '+str(TN))
    print('FP,'+str(ticker)+', '+str(FP))
    print('FN,'+str(ticker)+', '+str(FN))
    print('TP,'+str(ticker)+', '+str(TP))


