#include <iostream>
using namespace std;
int n;
int t = 1;
int k = 0;
int main()
{
  cin >> n;
  for (int i = 0; i < n; i++)
  {
    t *= i + 1;
    while (t % 10 == 0)
      t /= 10, k++;
    t %= 10;
  }
  cout<<t<<' '<<k;

  return 0;
}