import jax
import jax.random
import jax.numpy as jnp
import jax.experimental.checkify as checkify

from dejax import uniform_replay, clustered_replay
from dejax.utils import scalar_to_jax


def make_item(x):
    return scalar_to_jax(x)


def make_buffer():
    def clustering_fn(item):
        return jax.lax.select(item >= 2, 1, 0)

    cluster_buffer = uniform_replay(max_size=3)
    buffer = clustered_replay(2, cluster_buffer, clustering_fn)

    return buffer


def test_clustered_replay():
    buffer = make_buffer()

    buffer_state = buffer.init_fn(make_item(0))
    for item in [0, 1, 2]:
        buffer_state = buffer.add_fn(buffer_state, make_item(item))

    assert buffer.size_fn(buffer_state) == 3

    batch_size = 10000
    large_batch = buffer.sample_fn(buffer_state, jax.random.PRNGKey(1337), batch_size)
    assert large_batch.shape == (batch_size,)
    for item, prob in [(0, 0.25), (1, 0.25), (2, 0.5)]:
        assert jnp.allclose(jnp.sum(large_batch == item) / batch_size, prob, atol=0.01)


def test_clustered_replay_jit():
    batch_size = 10000

    @jax.jit
    @checkify.checkify
    def do_something_with_buffer():
        buffer = make_buffer()
        buffer_state = buffer.init_fn(make_item(0))
        for item in [0, 1, 2]:
            buffer_state = buffer.add_fn(buffer_state, make_item(item))
        size = buffer.size_fn(buffer_state)
        large_batch = buffer.sample_fn(buffer_state, jax.random.PRNGKey(1337), batch_size)
        return size, large_batch

    err, (size, large_batch) = do_something_with_buffer()
    err.throw()
    assert size == 3
    assert large_batch.shape == (batch_size,)


