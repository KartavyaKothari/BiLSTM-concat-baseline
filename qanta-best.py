# -*- coding: utf-8 -*-
"""CS 728 BiLSTM-concat-softmax baseline

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1FLO7vJpj7B-1M8QnsUbT0IVqN9j4cLQA

Downloading data
"""

# !wget www.cse.iitb.ac.in/~yashjain/copy_files/datasetXWikiWeb768.tsv
# !wget www.cse.iitb.ac.in/~yashjain/copy_files/id2ClassMappingsXifengWikiWeb768.txt
# !wget www.cse.iitb.ac.in/~yashjain/copy_files/dataset_GQ.tsv
# !wget www.cse.iitb.ac.in/~yashjain/copy_files/dataset_TQ.tsv
# !wget www.cse.iitb.ac.in/~yashjain/copy_files/dataset_qanta.tsv
# !wget www.cse.iitb.ac.in/~yashjain/copy_files/dataset_SQ.tsv

# # Glove dictionary
# !wget https://www.cse.iitb.ac.in/~kartavya/datafiles/glove_dict_tensor.pkl

"""Importing stuff"""

import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.utils.data import TensorDataset, random_split
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler

from sklearn.metrics import classification_report, accuracy_score, f1_score

import os
import datetime
import torchvision.transforms as transforms

"""Creating glove dictionary form scratch"""

# !wget http://nlp.stanford.edu/data/glove.6B.zip
# !unzip glove.6B.zip
# !pip install bcolz
# import pickle
# import numpy as np
# words = []
# idx = 0
# word2idx = {}
# vectors = []

# with open(f'glove.6B.50d.txt', 'rb') as f:
#     for l in f:
#         line = l.decode().split()
#         word = line[0]
#         words.append(word)
#         word2idx[word] = idx
#         idx += 1
#         vect = torch.from_numpy(np.array(line[1:]).astype(np.double))
#         vectors.append(vect)
    
# glove = {w: vectors[word2idx[w]] for w in words}
# f = open("glove_dict_tensor.pkl","wb")
# pickle.dump(glove,f)
# f.close()

"""Load the glove dictionary"""

import pickle
pickle_in = open("data/glove_dict_tensor.pkl","rb")
glove = pickle.load(pickle_in)

"""Hyperparameters"""

dataset_file = "data/dataset_qanta.tsv"
type_2_Id_File = "data/id2ClassMappingsXifengWikiWeb768.txt"
sentence_sequence_length = 25
glove_vector_len = 50
input_require_grad = False

input_dim = 50
hidden_dim = 50
layer_dim = 1

batch_size = 100
num_epochs = 100
learning_rate = 1e-6

print("dataset_file",dataset_file)
print("type_2_Id_File",type_2_Id_File)
print("sentence_sequence_length",sentence_sequence_length)
print("glove_vector_len", glove_vector_len)
print("input_require_grad",input_require_grad)

print("input_dim",input_dim)
print("hidden_dim",hidden_dim)
print("layer_dim",layer_dim)

print("batch_size",batch_size)
print("num_epochs",num_epochs)
print("learning_rate",learning_rate)

class Data:
  def __init__(self, datasetFile, type2IdFile, batchSize=batch_size):
    self.dataset_types = []
    self.queries = []
    self.t2_types = []
    self.type2Id = {}
    self.batchSize = batchSize
    self.datasetFile = datasetFile
    self.max_length = sentence_sequence_length
    self.batchSize=batchSize

    tmp = []
    with open(type2IdFile) as f:
      tmp = f.readlines()
    tmp = [x.strip() for x in tmp]
    NUM_CLASSES = len(tmp)
    for line in tmp:
      line = line.split("\t")
      self.type2Id[line[1]] = int(line[0])

  def loadData(self):
    content=[]
    with open(self.datasetFile) as f:
      content = f.readlines()
    content= [x.strip() for x in content]
   
    for line in content:
      line = line.split('\t')
      self.dataset_types.append(line[0])
      self.queries.append(line[1])
      self.t2_types.append(line[2])

    return self.preProcessData()
    
  def preProcessData(self):
    input_ids = []
    labels = []

    max_length = self.max_length 
    
    for q in self.queries:
      q_embedding = []
      q = q.strip()
      for i,w in enumerate(q.split(' ')):
        if i == max_length - 1:
          break
        try:
          q_embedding.append(glove[w.lower()])
        except:
          q_embedding.append(torch.zeros((glove_vector_len,),dtype=torch.double))
          # q_embedding.append(torch.from_numpy(np.random.normal(scale=0.6, size=(glove_vector_len, ))))
        
      q_embedding = torch.cat(q_embedding,dim=0).view(len(q_embedding),-1)
      
      if q_embedding.size(0) < max_length:
        q_embedding = torch.cat((q_embedding,torch.zeros((max_length-len(q_embedding),glove_vector_len),dtype=torch.double)),dim=0)
      
      input_ids.append(q_embedding)

    input_ids = torch.cat(input_ids, dim=0).view(len(input_ids),max_length,glove_vector_len)
  
    for t in self.t2_types:
      labels.append(self.type2Id[t])
    labels = torch.tensor(labels)

    dataset = TensorDataset(input_ids, labels)

    # return dataset
    return self.tvt_split(dataset)
  
  def tvt_split(self, dataset):
    tot = len(dataset)
    trainSize = int(round(0.7*tot))
    valSize = int(round(0.1*tot))
    testSize = tot - trainSize - valSize

    print(trainSize, valSize, testSize)
    trainSet, valSet, testSet = random_split(dataset, [trainSize, valSize, testSize])
    
    print("tvt lengths",len(trainSet), len(valSet), len(testSet))
    print("Batch size", self.batchSize)
    
    train_dataloader = DataLoader(
        trainSet,  # The training samples.
        sampler = RandomSampler(trainSet), # Select batches randomly #TODO RandomSampler
        batch_size = self.batchSize, # Trains with this batch size.
    )
    val_dataloader = DataLoader(
        valSet,
        sampler = SequentialSampler(valSet), #Select batches sequentially
        batch_size = self.batchSize
    )
    test_dataloader = DataLoader(
        testSet,
        sampler = SequentialSampler(testSet),
        batch_size = self.batchSize
    )
    print(len(train_dataloader), len(val_dataloader), len(test_dataloader))
    return train_dataloader, val_dataloader, test_dataloader

class NET(nn.Module):
  def __init__(self, input_dim, hidden_dim, layer_dim, batchSize=batch_size, seqLength=sentence_sequence_length, numClasses=661):
    super(NET,self).__init__()
    self.batchSize = batchSize
    self.hidden_dim = hidden_dim
    self.layer_dim = layer_dim

    self.bilstm = nn.LSTM(input_dim, hidden_dim, layer_dim, batch_first=True, bidirectional = True)
    self.fc = nn.Linear(seqLength*hidden_dim*2,numClasses)

  def forward(self, input_ids):
    # Initialize hidden state
    h0 = torch.zeros((self.layer_dim*2, input_ids.size(0), self.hidden_dim),dtype=torch.double).requires_grad_()
    # Initialize cell state
    c0 = torch.zeros((self.layer_dim*2, input_ids.size(0), self.hidden_dim),dtype=torch.double).requires_grad_()
    # BiLSTM
    out , (hn,cn) = self.bilstm(input_ids, (h0,c0))

    out = self.fc(out.reshape(out.size(0),-1))
    out = F.softmax(out,dim=1)

    return out

import random

model=NET(input_dim, hidden_dim, layer_dim)
model.double()

Set = Data(dataset_file, type_2_Id_File, batchSize=batch_size)
trainSet, valSet, testSet = Set.loadData()
optimizer=torch.optim.Adam(model.parameters(), lr=learning_rate)
loss_criterion = nn.CrossEntropyLoss()
seed_val = 42

# random.seed(seed_val)
np.random.seed(seed_val)
torch.manual_seed(seed_val)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10)

from tqdm import tqdm
import sys
import time
import os

np.set_printoptions(threshold=sys.maxsize)
p = []
valLossList = []
valAccList = []
start_time = datetime.datetime.now().strftime("%H%M%S-%d%m%Y")
for epochs in tqdm(range(num_epochs)):
  model.train()
  total_epoch_loss=0
  trainAcc = 0
  
  ############### Checking if the model weights are changing substantially or not
  if epochs==0 :
    for param in model.fc.parameters():
      z = param.data.detach().cpu().numpy()
      
      p = z
      break
    p = np.array(p)
  else:
    y = np.array([])    
    for param in model.fc.parameters():
      z = param.data.detach().cpu().numpy()
      y = z
      break
    y = np.array(y)
    x = (p-y)
    print("Change in weights norm:",np.linalg.norm(x))
    # if(np.linalg.norm(x)<5e-2):
    #   break
    p = y
  #################

  labels_flat = []
  pred_flat =  []
  loss=None
  
  for batch in trainSet:
    if input_require_grad == True:
      b_input_ids = batch[0].view(-1,sentence_sequence_length,glove_vector_len).requires_grad_()
    else:
      b_input_ids = batch[0].view(-1,sentence_sequence_length,glove_vector_len)

    b_labels = batch[1]
    if b_labels.shape[0]!=batch_size:
      print("label mismatch")
      continue #Otherwise creates problem with the model architecture
    
    optimizer.zero_grad()
    out = model(b_input_ids)
    
    loss=loss_criterion(out, b_labels)
    total_epoch_loss += loss.item()
    loss.backward()
    optimizer.step()

    preds = out.detach().numpy()
    labels_flat.extend(b_labels.numpy())
    pred_flat.extend(np.argmax(preds, axis=1).flatten())
    
  print(len(labels_flat), len(pred_flat))
  print("Train Accuracy:", accuracy_score(labels_flat, pred_flat))  
  print("Train F1-micro score:", f1_score(labels_flat, pred_flat, average='micro'))  
  avg_train_loss = total_epoch_loss / len(trainSet)
  print("Average Training loss:",avg_train_loss, "Total Training Loss: ", total_epoch_loss)

  model.eval()  
  labels_flat = []
  pred_flat =  []
  valLoss = 0
  for batch in valSet:
    b_input_ids = batch[0]
    b_labels = batch[1]
    #  = batch[2].to(device)
    if b_labels.shape[0]!=batch_size:
      continue #Otherwise creates problem with the model architecture

    with torch.no_grad():
      out = model(b_input_ids)
    preds = out.detach().numpy()
    pred_flat.extend(np.argmax(preds, axis=1).flatten())
    labels_flat.extend(b_labels.numpy())
    valLoss += loss_criterion(out, b_labels).item()

  
  print("Validation accuracy:", accuracy_score(labels_flat, pred_flat))
  print("Validation F1-micro score:", f1_score(labels_flat, pred_flat, average='micro'))
  print( "Validation Loss:", valLoss)

  # scheduler.step(acc)
  scheduler.step(valLoss)
  valLossList.append(valLoss)
  valAccList.append(accuracy_score(labels_flat, pred_flat))
  #saving the model
  if not os.path.exists('./checkpoints/'+start_time+"/"):
    os.makedirs('./checkpoints/'+start_time+"/")
  # torch.save({
  #     'epoch': epochs,
  #     'model_state_dict': model.state_dict(),
  #     'optimizer_state_dict': optimizer.state_dict(),
  #     'loss': loss,
  # }, './checkpoints/'+start_time+"/checkpt_"+str(epochs)+".pt")
  try:
    if valLoss[-1] > valLoss[-2] and valLoss[-1] > valLoss[-3] and valLoss[-1] > valLoss[-4]:
      print("Stopping training early...")
      break
  except Exception as e:
    pass

print("Min val Loss at:", np.argmin(np.array(valLossList),axis=0), "Min Val loss:", np.min(np.array(valLossList)))
print("Max val accuracy at:", np.argmax(np.array(valAccList),axis=0), "Max Val accuracy:", np.max(np.array(valAccList)))

def TestEvaluation(model, testSet):
  model.eval()
  pred_flat = []
  labels_flat = [] 
  
  for batch in testSet:
    b_input_ids = batch[0]
    # b_input_mask = batch[1].to(device)
    b_labels = batch[1]
    if b_labels.shape[0]!=batch_size:
      continue

    with torch.no_grad():
      out = model(b_input_ids)
    preds = out.detach().numpy()
    pred_flat.extend(np.argmax(preds, axis=1).flatten().tolist())
    labels_flat.extend(b_labels.cpu().numpy().flatten().tolist())

  print("Test Accuracy:", accuracy_score(labels_flat, pred_flat))
  print("Test F1-score micro:", f1_score(labels_flat, pred_flat, average='micro'))
# print(classification_report(labels_flat, pred_flat))
print('*'*20)
print("Complete iteration model")
TestEvaluation(model, testSet)
print('*'*20)
print("dataset_file",dataset_file)
print("type_2_Id_File",type_2_Id_File)
print("sentence_sequence_length",sentence_sequence_length)
print("glove_vector_len", glove_vector_len)
print("input_require_grad",input_require_grad)

print("input_dim",input_dim)
print("hidden_dim",hidden_dim)
print("layer_dim",layer_dim)

print("batch_size",batch_size)
print("num_epochs",num_epochs)
print("learning_rate",learning_rate)
