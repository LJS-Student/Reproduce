import os.path as osp

import torch
from torch_geometric.datasets import AMiner
from torch_geometric.nn import MetaPath2Vec


def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '..', 'data',
                    'AMiner')
    dataset = AMiner(path)
    data = dataset[0]
    print(data)

    metapath = [
        ('author', 'wrote', 'paper'),
        ('paper', 'published in', 'venue'),
        ('venue', 'published', 'paper'),
        ('paper', 'written by', 'author'),
    ]

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = MetaPath2Vec(data.edge_index_dict, embedding_dim=128,
                         metapath=metapath, walk_length=50, context_size=7,
                         walks_per_node=5, num_negative_samples=5,
                         sparse=True).to(device)

    loader = model.loader(batch_size=128, shuffle=True, num_workers=12)
    optimizer = torch.optim.SparseAdam(list(model.parameters()), lr=0.01)

    def train(epoch, log_steps=100, eval_steps=2000):
        model.train()

        total_loss = 0
        for i, (pos_rw, neg_rw) in enumerate(loader):
            optimizer.zero_grad()
            loss = model.loss(pos_rw.to(device), neg_rw.to(device))
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            if (i + 1) % log_steps == 0:
                print((f'Epoch: {epoch}, Step: {i + 1:05d}/{len(loader)}, '
                       f'Loss: {total_loss / log_steps:.4f}'))
                total_loss = 0

            if (i + 1) % eval_steps == 0:
                acc = test()
                print((f'Epoch: {epoch}, Step: {i + 1:05d}/{len(loader)}, '
                       f'Acc: {acc:.4f}'))

    @torch.no_grad()
    def test(train_ratio=0.1):
        model.eval()

        z = model('author', batch=data.y_index_dict['author'])
        y = data.y_dict['author']

        perm = torch.randperm(z.size(0))
        train_perm = perm[:int(z.size(0) * train_ratio)]
        test_perm = perm[int(z.size(0) * train_ratio):]

        return model.test(z[train_perm], y[train_perm], z[test_perm],
                          y[test_perm], max_iter=150)

    for epoch in range(1, 6):
        train(epoch)
        acc = test()
        print(f'Epoch: {epoch}, Accuracy: {acc:.4f}')


if __name__ == "__main__":
    main()