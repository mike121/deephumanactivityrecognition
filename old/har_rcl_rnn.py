#import theano.sandbox.cuda
#theano.sandbox.cuda.use('gpu0')
from models.rcl_rnn import RCL_RNN
from training.train import TrainModel
from lasagne.nonlinearities import rectify, softmax, leaky_rectify
import load_data as ld
import numpy as np


def main():
    add_pitch, add_roll, add_filter = True, True, True
    n_samples, step = 200, 50
    shuffle = True
    batch_size = 64
    (train_set, test_set, valid_set, (sequence_length, n_features, n_classes)), name = \
        ld.LoadHAR().uci_hapt(add_pitch=add_pitch, add_roll=add_roll, add_filter=add_filter,
                              n_samples=n_samples, step=step, shuffle=shuffle)

    # The data is structured as (samples, sequence, features) but to properly use the convolutional RNN we need a longer
    # time
    factor = 5
    sequence_length *= factor

    n_train = train_set[0].shape[0]//factor
    print("Resizing train set from %d to %d" % (train_set[0].shape[0], n_train*factor))
    train_set = (np.reshape(train_set[0][:factor*n_train], (n_train, sequence_length, n_features)),
                 np.reshape(train_set[1][:factor*n_train], (n_train, factor, n_classes)))

    n_test = test_set[0].shape[0]//factor
    print("Resizing test set from %d to %d" % (test_set[0].shape[0], n_test*factor))
    test_set = (np.reshape(test_set[0][:factor*n_test], (n_test, sequence_length, n_features)),
                np.reshape(test_set[1][:factor*n_test], (n_test, factor, n_classes)))
    valid_set = test_set

    n_train = train_set[0].shape[0]
    n_test = test_set[0].shape[0]
    n_valid = valid_set[0].shape[0]

    n_train_batches = n_train//batch_size
    n_test_batches = n_test//batch_size
    n_valid_batches = n_valid//batch_size

    print("n_train_batches: %d, n_test_batches: %d, n_valid_batches: %d"
          % (n_train_batches, n_test_batches, n_valid_batches))

    n_conv = 1
    model = RCL_RNN(n_in=(sequence_length, n_features),
                    n_filters=[64]*n_conv,
                    filter_sizes=[3]*n_conv,
                    pool_sizes=[2]*n_conv,
                    n_hidden=[100],
                    conv_dropout=0.4,
                    rcl=[3, 3, 3, 3, 3],
                    rcl_dropout=0.4,
                    dropout_probability=0.5,
                    n_out=n_classes,
                    downsample=1,
                    trans_func=rectify,
                    out_func=softmax,
                    batch_size=batch_size,
                    factor=factor)

    f_train, f_test, f_validate, train_args, test_args, validate_args = model.build_model(train_set,
                                                                                          test_set,
                                                                                          valid_set)
    train_args['inputs']['batchsize'] = batch_size
    train_args['inputs']['learningrate'] = 0.004
    train_args['inputs']['beta1'] = 0.9
    train_args['inputs']['beta2'] = 1e-6

    test_args['inputs']['batchsize'] = batch_size
    validate_args['inputs']['batchsize'] = batch_size

    model.log += "\nDataset: %s" % name
    model.log += "\nTraining samples: %d" % n_train
    model.log += "\nTest samples: %d" % n_test
    model.log += "\nSequence length: %d" % (sequence_length/factor)
    model.log += "\nTime steps: %d" % factor
    model.log += "\nStep: %d" % step
    model.log += "\nShuffle: %s" % shuffle
    model.log += "\nAdd pitch: %s\nAdd roll: %s" % (add_pitch, add_roll)
    model.log += "\nAdd filter separated signals: %s" % add_filter
    model.log += "\nTransfer function: %s" % model.transf
    train = TrainModel(model=model,
                       anneal_lr=0.75,
                       anneal_lr_freq=50,
                       output_freq=1,
                       pickle_f_custom_freq=100,
                       f_custom_eval=None)
    train.pickle = True
    train.add_initial_training_notes("")
    train.train_model(f_train, train_args,
                      f_test, test_args,
                      f_validate, validate_args,
                      n_train_batches=n_train_batches,
                      n_test_batches=n_test_batches,
                      n_valid_batches=n_valid_batches,
                      n_epochs=2000)

if __name__ == "__main__":
    main()
