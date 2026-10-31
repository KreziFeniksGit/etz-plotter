import sys
input=sys.stdin.readline
n,m=map(int,input().split())
lst=[]
for i in range(n):
    lst.append(list(map(int,input().split())))
plst=[[0]*(m+1) for i in range(n+1)]
for i in range(1,n+1):
    for j in range(1,m+1):
        plst[i][j]=lst[i-1][j-1]+plst[i-1][j]+plst[i][j-1]-plst[i-1][j-1]
k=int(input())
otv=[]
for i in range(k):
    r1,c1,r2,c2=map(int,input().split())
    sm=plst[r2][c2]-plst[r1-1][c2]-plst[r2][c1-1]+plst[r1-1][c1-1]
    sm//=(r2-r1+1)*(c2-c1+1)
    otv.append(str(sm))
print("\n".join(otv))
