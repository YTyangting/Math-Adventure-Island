#include<iostream>
using namespace std;

class Time
{
public:
	int h1, m1, s1;
	int h2, m2, s2;
	int x;
	void Output();
};

void Time::Output()
{
	cout << (h2 * 3600 + m2 * 60 + s2) - (h1 * 3600 + m1 * 60 + s1);
}

int main()
{
	Time A;
	cin >> A.h1 >> A.m1 >> A.s1;
	cin >> A.h2 >> A.m2 >> A.s2;
	A.Output();
}
