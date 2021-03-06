import pickle
import numpy as np
import torch
import torch.nn as nn
from model.model import GTN
from utils.utils import f1_score, true_positive_rate, false_positive_rate
import matplotlib.pyplot as plt

epochs = 50
node_dim = 64
num_channels = 2
lr = 0.005
weight_decay = 0.001
num_layers = 2
norm = True
adaptive_lr = True

dataset = input("Choose any one of the datasets: ACM ,IMDB, DPLB")

with open('data/'+dataset+'/node_features.pkl', 'rb') as f:
    node_features = pickle.load(f)
with open('data/'+dataset+'/edges.pkl', 'rb') as f:
    edges = pickle.load(f)
with open('data/'+dataset+'/labels.pkl', 'rb') as f:
    labels = pickle.load(f)

num_nodes = edges[0].shape[0]

for i,edge in enumerate(edges):
    if i ==0:
        A = torch.from_numpy(edge.todense()).type(torch.FloatTensor).unsqueeze(-1)
    else:
        A = torch.cat([A,torch.from_numpy(edge.todense()).type(torch.FloatTensor).unsqueeze(-1)], dim=-1)
A = torch.cat([A,torch.eye(num_nodes).type(torch.FloatTensor).unsqueeze(-1)], dim=-1)

node_features = torch.from_numpy(node_features).type(torch.FloatTensor)
train_node = torch.from_numpy(np.array(labels[0])[:,0]).type(torch.LongTensor)
train_target = torch.from_numpy(np.array(labels[0])[:,1]).type(torch.LongTensor)
valid_node = torch.from_numpy(np.array(labels[1])[:,0]).type(torch.LongTensor)
valid_target = torch.from_numpy(np.array(labels[1])[:,1]).type(torch.LongTensor)
test_node = torch.from_numpy(np.array(labels[2])[:,0]).type(torch.LongTensor)
test_target = torch.from_numpy(np.array(labels[2])[:,1]).type(torch.LongTensor)

num_classes = torch.max(train_target).item()+1
final_f1 = 0

model = GTN(num_edge=A.shape[-1],
            num_channels=num_channels,
            w_in=node_features.shape[1],
            w_out=node_dim,
            num_class=num_classes,
            num_layers=num_layers,
            norm=norm)
if adaptive_lr == 'false':
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=0.001)
else:
    optimizer = torch.optim.Adam([{'params': model.weight},
                                  {'params': model.linear1.parameters()},
                                  {'params': model.linear2.parameters()},
                                  {"params": model.layers.parameters(), "lr": 0.5}
                                  ], lr=0.005, weight_decay=0.001)
loss = nn.CrossEntropyLoss()
# Train & Valid & Test
best_val_loss = 10000
best_test_loss = 10000
best_train_loss = 10000
best_train_f1 = 0
best_val_f1 = 0
best_test_f1 = 0
valloss =[]
testloss =[]
trainloss =[]
trainf1=[]
testf1=[]
valf1=[]
train_tpr=[]
train_fpr=[]
val_tpr=[]
val_fpr=[]
test_tpr=[]
test_fpr=[]


for i in range(epochs):
    for param_group in optimizer.param_groups:
        if param_group['lr'] > 0.005:
             param_group['lr'] = param_group['lr'] * 0.9
    print('Epoch:  ',i+1)
    model.zero_grad()
    model.train()
    loss,y_train,Ws = model(A, node_features, train_node, train_target)
    train_f1 = torch.mean(f1_score(torch.argmax(y_train.detach(),dim=1), train_target, num_classes=num_classes)).cpu().numpy()
    trainloss.append(loss.detach().cpu().numpy())
    trainf1.append(train_f1)
    print('Train - Loss: {}, Macro_F1: {}'.format(loss.detach().cpu().numpy(), train_f1))
    loss.backward()
    optimizer.step()
    model.eval()
    # Valid
    with torch.no_grad():
        val_loss, y_valid,_ = model.forward(A, node_features, valid_node, valid_target)
        val_f1 = torch.mean(f1_score(torch.argmax(y_valid,dim=1), valid_target, num_classes=num_classes)).cpu().numpy()
        valloss.append(val_loss.detach().cpu().numpy())
        valf1.append(val_f1)
        print('Valid - Loss: {}, Macro_F1: {}'.format(val_loss.detach().cpu().numpy(), val_f1))
        test_loss, y_test,W = model.forward(A, node_features, test_node, test_target)
        test_f1 = torch.mean(f1_score(torch.argmax(y_test,dim=1), test_target, num_classes=num_classes)).cpu().numpy()
        testloss.append(test_loss.detach().cpu().numpy())
        testf1.append(test_f1)
        print('Test - Loss: {}, Macro_F1: {}\n'.format(test_loss.detach().cpu().numpy(), test_f1))
        if val_f1 > best_val_f1:
            best_val_loss = val_loss.detach().cpu().numpy()
            best_test_loss = test_loss.detach().cpu().numpy()
            best_train_loss = loss.detach().cpu().numpy()
            best_train_f1 = train_f1
            best_val_f1 = val_f1
            best_test_f1 = test_f1

print('---------------Best Results--------------------')
print('Train - Loss: {}, Macro_F1: {}'.format(best_train_loss, best_train_f1))
print('Valid - Loss: {}, Macro_F1: {}'.format(best_val_loss, best_val_f1))
print('Test - Loss: {}, Macro_F1: {}'.format(best_test_loss, best_test_f1))
final_f1 += best_test_f1

x = np.linspace(1,epochs)
plt.plot(x,trainloss,'r-',label="Training loss")
plt.plot(x,valloss,'b-',label="Validation Loss")
plt.plot(x,testloss,'g-',label="Test Loss")
plt.title("Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.legend()
plt.show()

x = np.linspace(1,epochs)
plt.plot(x,trainf1,'r-',label="Training MacroF1")
plt.plot(x,valf1,'b-',label="Validation MacroF1")
plt.plot(x,testf1,'g-',label="Test MacroF1")
plt.title("MacroF1 with epochs")
plt.xlabel("Epoch")
plt.ylabel("MacroF1")
plt.legend()
plt.show()