__author__ = 'ZY'



def api(fun):
    def wrapper(*args,**kwargs):
        print 'api'
        return fun(*args,**kwargs)
    return wrapper
@api
def a():
    print 'aa'

if __name__=='__main__':
    a()




