The action generate_gestures.py receives the text input and producing the robot's gestures associated with the robot speech.

## Dependencies
* Python 2.7
* Tensorflow (1.13.2)
* Theano (1.0.4)
* numpy
* scipy
* math
* pickle
* nltk

## Getting started
This action uses [skipthought vector](https://github.com/ryankiros/skip-thoughts) as the sentence embedding. Firstly, create the folder named skipthoughts inside folder data. Downloading the related files by executing the following:

    mkdir skipthoughts
    cd skipthoughts
    wget http://www.cs.toronto.edu/~rkiros/models/dictionary.txt
    wget http://www.cs.toronto.edu/~rkiros/models/utable.npy
    wget http://www.cs.toronto.edu/~rkiros/models/btable.npy
    wget http://www.cs.toronto.edu/~rkiros/models/uni_skip.npz
    wget http://www.cs.toronto.edu/~rkiros/models/uni_skip.npz.pkl
    wget http://www.cs.toronto.edu/~rkiros/models/bi_skip.npz
    wget http://www.cs.toronto.edu/~rkiros/models/bi_skip.npz.pkl

## Running
Executing the generate_gestures.py action with the robot IP and PORT:

    python generate_gestures.py --ip --port

Typying the random text (e.g: a person is waving the left hand, a person is waving their right hand, they are waving the both two hands, a person is dancing cha-cha-cha, a person is taking a bow). The robot will perform the gesture associated with its speech.

Typing exit to stop executing the action
## License
[Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0)
