#include <iostream>
#include <string.h>
using namespace std;

char st[1000];

void fun(int x,int y)
{
  for(int j=y;j>=x;j--){
    cout<<st[j];
  }
}

int main()
{
  cin.getline(st, 1000);
  // cout << st;
  for (int i = 0; i < strlen(st); i++)
  {
    if (st[i] == ' ')
      cout << ' ';
    else
    {
      int k = i;
      while (st[i] != ' ' && i < strlen(st))
        i++;
      i--;
      fun(k, i);
    }
  }

  return 0;
}
