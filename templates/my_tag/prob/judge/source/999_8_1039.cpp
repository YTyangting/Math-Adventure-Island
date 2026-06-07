#include <iostream>
#include <iomanip>
using namespace std;
int a[1000][1000];
int n;
void fun(){
  int l[4][2] = {0,1,1,0,0,-1,-1,0},g = 0;
  int j=1,x=0,y=0,dx=0,dy=1;
  for(int i=0;i<n*n;i++){
    a[x][y] = j++;
    if(x+dx>=n||x+dx<0||y+dy<0||y+dy>=n||a[x+dx][y+dy]!=0){
      g = (g+1)%4;
      dx = l[g][0];
      dy = l[g][1];
    }
    x+=dx,y+=dy;
  }
}


int main(){
  cin>>n;
    fun();
    for(int i=0;i<n;i++){
      for(int j=0;j<n;j++){
        cout<<setw(4)<<a[i][j]<<"  ";
      }
      cout<<'\n';
    }

  return 0;
}
