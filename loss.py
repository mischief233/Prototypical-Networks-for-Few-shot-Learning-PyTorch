import torch
import numpy as np
from torch.autograd import Variable
from torch.nn import functional as F

'''
Inspired by https://github.com/jakesnell/prototypical-networks/blob/master/protonets/models/few_shot.py
'''


def euclidean_dist(x, y):
    '''
    Compute euclidean distance between two tensors
    '''
    # x: N x D
    # y: M x D
    n = x.size(0)
    m = y.size(0)
    d = x.size(1)
    if d != y.size(1):
        raise Exception

    x = x.unsqueeze(1).expand(n, m, d)
    y = y.unsqueeze(0).expand(n, m, d)

    return torch.pow(x - y, 2).sum(2)


def protypical_loss(output, target, n_support):
    cputargs = target.cpu() if target.is_cuda else target
    cpuoutput = output.cpu() if target.is_cuda else output

    def supp_idxs(c):
        return torch.LongTensor(np.where(cputargs.numpy() == c)[0][:n_support])

    classes = np.unique(cputargs)
    n_classes = len(classes)
    n_query = len(np.where(cputargs.numpy() == classes[0])[0]) - n_support
    os_idxs = list(map(supp_idxs, classes))
    prototypes = [cpuoutput[i].mean(0).data.numpy().tolist() for i in os_idxs]
    prototypes = Variable(torch.FloatTensor(prototypes))

    oq_idxs = map(lambda c: np.where(cputargs.numpy() == c)[0][n_support:], classes)
    oq = output[np.array(list(oq_idxs)).flatten()]

    if target.is_cuda:
        prototypes = prototypes.cuda()

    dists = euclidean_dist(oq, prototypes)

    log_p_y = F.log_softmax(-dists).view(n_classes, n_query, -1)

    target_inds = torch.arange(0, n_classes).view(
        n_classes, 1, 1).expand(n_classes, n_query, 1).long()
    target_inds = Variable(target_inds, requires_grad=False)
    if target.is_cuda:
        target_inds = target_inds.cuda()

    loss_val = -log_p_y.gather(2, target_inds).squeeze().view(-1).mean()
    _, y_hat = log_p_y.max(2)

    acc_val = torch.eq(y_hat, target_inds.squeeze()).float().mean()

    return loss_val,  acc_val
