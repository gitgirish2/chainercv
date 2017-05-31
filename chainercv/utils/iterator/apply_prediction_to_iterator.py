import itertools
from operator import itemgetter


def apply_prediction_to_iterator(predict, iterator, hook=None):
    """Apply a prediction function/method to an iterator.

    This function applies a prediction function/method to an iterator.
    It assumes that the iterator returns a batch of images or
    a tuple whose first element is a batch of images. In the case that
    it returns a tuple, the rests are treated as ground truth
    values.

    >>> imgs = next(iterator)
    >>> # imgs: [img]
    or
    >>> imgs, gt_vals0, gt_vals1 = next(iterator)
    >>> # gt_vals0: [gt_val0]
    >>> # gt_vals1: [gt_val1]

    This function applys :func:`predict` to a batch of images and gets
    predicted value(s). :func:`predict` should take a batch of images and
    return a batch of prediction values
    or a tuple of batches of prediction values.

    >>> pred_vals0 = predict(imgs)
    >>> # pred_vals0: [pred_val0]
    or
    >>> pred_vals0, pred_vals1 = predict(imgs)
    >>> # pred_vals0: [pred_val0]
    >>> # pred_vals1: [pred_val1]

    Args:
        predict: A callable which takes a batch of images and returns
            prediction.
        iterator (chainer.Iterator): An iterator. Each sample should have
            an image as its first element. This image is passed to
            :func:`predict` as an argument.
            The rests are treated as ground truth values.
        hook: A callable which is called after each iteration.
            :obj:`imgs`, :obj:`pred_labels` and :obj:`gt_values` are passed as
            arguments.
            Note that these values do not contain data from the previous
            iterations.

    Returns:
        An iterator and two tuples of iterators:
        This function returns an iterator and two tuples of iterators:
        :obj:`imgs`, :obj:`pred_values` and :obj:`gt_values`.
        :obj:`imgs` is an iterator which returns an image.
        :obj:`pred_values` is a tuple of iterators. Each iterator
        returns a corresponding predicted value.
        For example, if :func:`predict` returns
        :obj:`([pred_val0], [pred_val1])`, :obj:`next(pred_values[0])`
        and :obj:`next(pred_values[1])`
        will be :obj:`pred_val0` and :obj:`pred_val1`.
        :obj:`gt_values` is a tuple of iterators. Each iterator
        returns a corresponding ground truth value. If the input
        iterator does not give any ground truth values, this tuple
        will be empty.
    """

    imgs, pred_values, gt_values = _unzip(_apply(predict, iterator, hook))

    # imgs: iter of [img] -> iter of img
    imgs = itertools.chain.from_iterable(imgs)

    # pred_values: iter of ([pred_val0], [pred_val1], ...)
    #    -> (iter of pred_val0, iter of pred_val1, ...)
    pred_values = tuple(
        map(itertools.chain.from_iterable, _unzip(pred_values)))

    # gt_values: iter of ([gt_val0], [gt_val1], ...)
    #    -> (iter of gt_val0, iter of gt_val1, ...)
    gt_values = tuple(map(itertools.chain.from_iterable, _unzip(gt_values)))

    return imgs, pred_values, gt_values


def _apply(predict, iterator, hook):
    for batch in iterator:
        # batch: [(img, gt_val0, gt_val1, ...)] or [img]

        imgs = list()
        gt_values = list()
        for sample in batch:
            if isinstance(sample, tuple):
                imgs.append(sample[0])
                gt_values.append(sample[1:])
            else:
                imgs.append(sample)
                gt_values.append(tuple())

        # imgs: [img]

        # gt_values: [(gt_val0, gt_val1, ...)] -> ([gt_val0], [gt_val1], ...)
        gt_values = tuple(list(v) for v in zip(*gt_values))

        # pred_values: ([pred_val0], [pred_val1], ...) or [pred_val]
        pred_values = predict(imgs)
        if not isinstance(pred_values, tuple):
            # pred_values: [pred_val] -> ([pred_val0], [pred_val1], ...)
            pred_values = pred_values,

        if hook:
            hook(imgs, pred_values, gt_values)

        yield imgs, pred_values, gt_values


def _unzip(iterable):
    iterator = iter(iterable)

    # to detect the number of items, pop the first sample
    heads = next(iterator)
    n_item = len(heads)

    # concatenate popped sample with the iterator
    iterator = itertools.chain([heads], iterator)

    return tuple(
        map(itemgetter(i), iter_)
        for i, iter_ in enumerate(itertools.tee(iterator, n_item)))
