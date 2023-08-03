
import threading

class ButtonPressThread(threading.Thread):
    def run(self):
        while True:
            print('Hello')
            x = input('This input will not block other stuff?')
            print(x)
            if x == 'q':
                break

be_thread = ButtonPressThread()
be_thread.start()