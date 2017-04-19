import numpy as np
#Rahul G. Krishnan
#Calculate the variance of the AUC
#Made based on pROC[http://www.biomedcentral.com/content/pdf/1471-2105-12-77.pdf]

#Sample to test against pROC implementation
'''
X = []
Y=[]

temp='3 2 4 5 5 5 5 2 5 2 1 2 5 4 4 2 5 5 5 2 5 2 5 2 4 5 4 4 1 4 4 2 2 5 5 2 2 5 5 5 5'
for t in temp.split(' '):
	X.append(int(t))

temp='1 1 1 1 5 1 2 2 1 2 2 1 1 1 2 1 2 1 1 3 4 1 4 1 5 5 1 1 2 4 1 1 2 2 1 2 1 2 2 1 1 1 1 2 1 2 1 1 3 2 4 2 1 4 1 1 5 4 2 2 1 1 1 3 1 2 2 4 4 1 1 1'
for t in temp.split(' '):
	Y.append(int(t))

AUC_verify=0.8236
'''

#X is the list of probabilities for the positive cases |X| = m
#Y is the list of probabilities for the negative cases |Y| = n
#Make sure X and Y are lists and not numpy arrays
#AUC_verify is the AUC calculated via sklearn/other method

def calcAUCVAR(X,Y,AUC_verify):
	m = len(X)
	n = len(Y)
        
	#Compute equal and greater matrices
	equal   = np.zeros((m,n))
	greater = np.zeros((m,n))

	for i in range(m): #X
		for j in range(n): #Y
			if X[i] == Y[j]:
				equal[i,j] = 0.5
			if X[i] > Y[j]:
				greater[i,j] = 1

	#Use U statistic to compute AUC independantly as theta
	MW = equal + greater

	theta = sum(sum(MW))/(m*n)

	#Verify that theta calculated is approximately the same as the AUC_verify calculated independantly
	if abs(AUC_verify-theta) >= 0.001:
		print "Difference between theta and AUC significant",abs(AUC_verify-theta)

	V_X = np.sum(MW,axis=1)/n
	V_Y = np.sum(MW,axis=0)/m

	S_X = sum((V_X-theta)*(V_X-theta))/(m-1)
	S_Y = sum((V_Y-theta)*(V_Y-theta))/(n-1)

	S = S_X/m + S_Y/n
	return S

def main():
	X = []
	Y=[]

	temp='3 2 4 5 5 5 5 2 5 2 1 2 5 4 4 2 5 5 5 2 5 2 5 2 4 5 4 4 1 4 4 2 2 5 5 2 2 5 5 5 5'
	for t in temp.split(' '):
		X.append(int(t))

	temp='1 1 1 1 5 1 2 2 1 2 2 1 1 1 2 1 2 1 1 3 4 1 4 1 5 5 1 1 2 4 1 1 2 2 1 2 1 2 2 1 1 1 1 2 1 2 1 1 3 2 4 2 1 4 1 1 5 4 2 2 1 1 1 3 1 2 2 4 4 1 1 1'
	for t in temp.split(' '):
		Y.append(int(t))

	AUC_verify=0.8236

	print calcAUCVAR(X,Y,AUC_verify)


if __name__ == '__main__':
	main()