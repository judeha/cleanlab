
# coding: utf-8

# ## Noise Generation
# 
# #### Contains methods for generating valid (learning with noise is possible) noise matrices, generating noisy labels given a noise matrix, generating valid noise matrices with a specific trace value, and more.

# In[ ]:


from __future__ import print_function, absolute_import, division, unicode_literals, with_statement
import numpy as np

from confidentlearning.util import value_counts


# In[ ]:


def noise_matrix_is_valid(noise_matrix, py, verbose = False):
    '''Given a prior py = p(y=k), returns true if the given noise_matrix is a learnable matrix.
    Learnability means that it is possible to achieve better than random performance, on average,
    for the amount of noise in noise_matrix.'''

    # Number of classes
    K = len(py)

    # Let's assume some number of training examples for code readability, 
    # but it doesn't matter what we choose as its not actually used.
    N = float(10000)

    ps = np.dot(noise_matrix, py) # P(y=k)

    #P(s=k, y=k')
    joint_noise = np.multiply(noise_matrix, py) # / float(N)

    # Check that joint_probs is valid probability matrix
    if not (abs(joint_noise.sum() - 1.0) < 1e-6):
        return False

    # Check that noise_matrix is a valid matrix
    # i.e. check p(s=k)*p(y=k) < p(s=k, y=k)
    for i in range(K):
        C = N * joint_noise[i][i]
        E1 = N * joint_noise[i].sum() - C
        E2 = N * joint_noise.T[i].sum() - C
        O = N - E1 - E2 - C
        if verbose:
            print("E1E2/C", E1*E2/C,"E1", E1, "E2", E2, "C", C, "|", E1*E2/C + E1 + E2 + C, "|",  E1*E2/C, "<", O)
            print(ps[i] * py[i], "<", joint_noise[i][i], ":", ps[i] * py[i] < joint_noise[i][i])

        if not (ps[i] * py[i] < joint_noise[i][i]):
            return False

    return True


# In[ ]:


def generate_noisy_labels(y, noise_matrix, verbose=False):  
    '''Generates noisy labels s (shape (N, 1)) from perfect labels y,
    'exactly' yielding the provided noise_matrix between s and y.

    Parameters
    ----------

    y : np.array (shape (N, 1))
        Perfect labels, without any noise. Contains K distinct natural number
        classes, e.g. 0, 1,..., K-1

    noise_matrix : np.array of shape (K, K), K = number of classes 
        A conditional probablity matrix of the form P(s=k_s|y=k_y) containing
        the fraction of examples in every class, labeled as every other class.
        Assumes columns of noise_matrix sum to 1.'''
  
    # Number of classes
    K = len(noise_matrix)

    # Compute p(y=k)
    py = value_counts(y) / float(len(y))

    # Generate s
    count_joint = (noise_matrix * py * len(y)).round().astype(int) # count(s and y)
    s = np.array(y)
    for k_s in range(K):
        for k_y in range(K):
            if k_s != k_y:
                s[np.random.choice(np.where((s==k_y)&(y==k_y))[0], count_joint[k_s][k_y], replace=False)] = k_s

    # Compute the actual noise matrix induced by s
    from sklearn.metrics import confusion_matrix
    counts = confusion_matrix(s, y).astype(float)
    new_noise_matrix = counts / counts.sum(axis=0)

    # Validate that s indeed produces the correct noise_matrix (or close to it)
    if np.linalg.norm(noise_matrix - new_noise_matrix) > 1:
        raise ValueError("s does not yield the same noise_matrix. " +
            "The difference in norms is " + str(np.linalg.norm(noise_matrix - new_noise_matrix)))

    return s  


# In[ ]:


def generate_noise_matrix_from_trace(
    K,                                      
    trace,  
    max_trace_prob=1.0,
    min_trace_prob=1e-5,
    max_noise_rate=1-1e-5,                                      
    min_noise_rate=0.0,                                      
    valid_noise_matrix=True, 
    py=None,
    frac_zero_noise_rates=0.,
): 
    '''Generates a K x K noise matrix P(s=k_s|y=k_y) with trace
    as the np.mean(np.diagonal(noise_matrix)).

    Parameters
    ----------

    K : int
      Creates a noise matrix of shape (K, K). Implies there are 
      K classes for learning with noisy labels. 

    trace : float (0.0, 1.0]
      Sum of diagonal entries of np.array of random probabilites that is returned.

    max_trace_prob : float (0.0, 1.0]
      Maximum probability of any entry in the trace of the return matrix.

    min_trace_prob : float [0.0, 1.0)
      Minimum probability of any entry in the trace of the return matrix.

    max_noise_rate : float (0.0, 1.0]
      Maximum noise_rate (non-digonal entry) in the returned np.array.

    min_noise_rate : float [0.0, 1.0)
      Minimum noise_rate (non-digonal entry) in the returned np.array.

    valid_noise_matrix : bool
      If True, returns a matrix having all necessary conditions for
      learning with noisy labels. In particular, p(y=k)p(s=k) < p(y=k,s=k)
      is satisfied. This requires that Trace > 1.

    py : np.array (shape (K, 1))
      The fraction (prior probability) of each true, hidden class label, P(y = k).
      REQUIRED when valid_noise_matrix == True.

    frac_zero_noise_rates : float
      The fraction of the n*(n-1) noise rates that will be set to 0. Note that if
      you set a high trace, it may be impossible to also have a low
      fraction of zero noise rates without forcing all non-"1" diagonal values. 
      Instead, when this happens we only guarantee to produce a noise matrix with
      frac_zero_noise_rates **or higher**. The opposite occurs with a small trace.

    Output
    ------
    np.array (shape (K, K)) 
      noise matrix P(s=k_s|y=k_y) with trace 
      as the np.sum(np.diagonal(noise_matrix)).
      This a conditional probability matrix and a
      left stochastic matrix.'''


    if valid_noise_matrix and trace <= 1:
        raise ValueError("trace > 1 is necessary for a" +
              " valid noise matrix to be returned (valid_noise_matrix == True)")
    
    if valid_noise_matrix and py is None:
        raise ValueError("py must be provided (not None) if the input parameter" +
              " valid_noise_matrix == True")
  
    while True:
        noise_matrix = np.zeros(shape=(K, K))
        
        # Randomly generate noise_matrix diagonal.
        nm_diagonal = generate_n_rand_probabilities_that_sum_to_m(
            n=K, 
            m=trace, 
            max_prob=max_trace_prob, 
            min_prob=min_trace_prob,
        )
        np.fill_diagonal(noise_matrix, nm_diagonal)
        
        # Randomly distribute number of zero-noise-rates across columns
        num_col_with_noise = K - np.count_nonzero(1 == nm_diagonal)
        num_zero_noise_rates = int(K * (K - 1) * frac_zero_noise_rates)
        # Remove zeros already in [1,0,..,0] columns
        num_zero_noise_rates -= (K - num_col_with_noise) * (K - 1) 
        num_zero_noise_rates = np.maximum(num_zero_noise_rates, 0) # Prevent negative
        num_zero_noise_rates_per_col = randomly_distribute_N_balls_into_K_bins(
            N = num_zero_noise_rates,
            K = num_col_with_noise,
            max_balls_per_bin = K - 2, # 2 = one for diagonal, and one to sum to 1
            min_balls_per_bin = 0,
        ) if K > 2 else np.array([1,1]) # special case for K = 2
        stack_nonzero_noise_rates_per_col = list(K - 1 - num_zero_noise_rates_per_col)[::-1]
        # Randomly generate noise rates for columns with noise.
        for col in np.arange(K)[nm_diagonal != 1]:
            num_noise = stack_nonzero_noise_rates_per_col.pop()
            # Generate num_noise noise_rates for the given column.
            noise_rates_col = list(generate_n_rand_probabilities_that_sum_to_m(
                n=num_noise, 
                m=1-nm_diagonal[col], 
                max_prob=max_noise_rate, 
                min_prob=min_noise_rate,
            ))
            # Randomly select which rows of the noisy column to assign the random noise rates
            rows = np.random.choice([row for row in range(K) if row!=col], num_noise, replace=False)
            for row in rows:
                noise_matrix[row][col] = noise_rates_col.pop()
        if not valid_noise_matrix or noise_matrix_is_valid(noise_matrix, py):
            break
      
    return noise_matrix


def generate_n_rand_probabilities_that_sum_to_m(
    n, 
    m, 
    max_prob = 1.0, 
    min_prob = 0.0,
):
    '''When min_prob=0 and max_prob = 1.0, this method is deprecated.
    Instead use np.random.dirichlet(np.ones(n))*m

    Generates 'n' random probabilities that sum to 'm'.

    Parameters
    ----------

    n : int
      Length of np.array of random probabilities to be returned. 

    m : float
      Sum of np.array of random probabilites that is returned.

    max_prob : float (0.0, 1.0] | Default value is 1.0
      Maximum probability of any entry in the returned np.array.

    min_prob : float [0.0, 1.0) | Default value is 0.0
      Minimum probability of any entry in the returned np.array.'''
  
    epsilon = 1e-8 # Imprecision allowed for inequalities with floats

    if n == 0:
        return np.array([])    
    if (max_prob + epsilon) < m / float(n):
        raise ValueError("max_prob must be greater or equal to m / n, but " +
                         "max_prob = "+str(max_prob)+", m = "+str(m)+", n = " +
                         str(n)+", m / n = "+str(m/float(n)))
    if min_prob > (m + epsilon) / float(n):
        raise ValueError("min_prob must be less or equal to m / n, but " +
                         "max_prob = "+str(max_prob)+", m = "+str(m)+", n = " +
                         str(n)+", m / n = "+str(m/float(n)))
    if min_prob >= (max_prob + epsilon):
        raise ValueError("min_prob must be less than max_prob, but " +
                         "max_prob = "+str(max_prob)+", m = "+str(m)+", n = " +
                         str(n)+", m / n = "+str(m/float(n)))

    # When max_prob = 1, min_prob = 0, the following two lines are equivalent to:
    #   intermediate = np.sort(np.append(np.random.uniform(0, 1, n-1), [0, 1]))
    #   result = (intermediate[1:] - intermediate[:-1]) * m
    result = np.random.dirichlet(np.ones(n))*m

    max_val = max(result) 
    while max_val > (max_prob + epsilon):
        result[np.argmin(result)] = min(result) + (max_val - max_prob)
        result[np.argmax(result)] = max_prob   
        max_val = max(result)

    min_val = min(result)
    while min_val < (min_prob - epsilon):
        result[np.argmax(result)] = max(result) - (min_prob - min_val)
        result[np.argmin(result)] = min_prob   
        min_val = min(result)

    return result


def randomly_distribute_N_balls_into_K_bins(
    N, # int
    K, # int
    max_balls_per_bin = None,
    min_balls_per_bin = None,
):
    '''Returns a uniformly random numpy integer array of length N that sums to K.'''
    
    if N == 0:
        return np.zeros(K, dtype=int)
    if max_balls_per_bin is None:
        max_balls_per_bin = N
    else:
        max_balls_per_bin = min(max_balls_per_bin, N)
    if min_balls_per_bin is None:
        min_balls_per_bin = 0
    else:
        min_balls_per_bin = min(min_balls_per_bin, N/K)
    if N/float(K) > max_balls_per_bin:
        N = max_balls_per_bin * K
    
    arr = np.round(generate_n_rand_probabilities_that_sum_to_m(
        n = K, 
        m = 1, 
        max_prob = max_balls_per_bin/float(N),
        min_prob = min_balls_per_bin/float(N),
    ) * N)
    while sum(arr) != N:
        while sum(arr) > N:
            arr[np.argmax(arr)] -= 1
        while sum(arr) < N:
            arr[np.argmin(arr)] += 1
    return arr.astype(int)


# #### Deprecated functions below

# In[ ]:


def generate_noise_matrix(
    K,
    max_noise_rate = 1.0,
    frac_zero_noise_rates = 0.0,
    verbose = False,
):
    '''DEPRECATED - Use generate_noise_matrix_from_trace()

    Generates a noise matrix by randomly assigning noise rates
    up to max_noise_rate, then setting noise rates to zero until
    zero until P(s!=k|s=k) < 1 is satisified. Additionally,
    frac_zero_noise_rates are set to zero.

    Parameters
    ----------

    K : int
      Creates a noise matrix of shape (K, K). Implies there are 
      K classes for learning with noisy labels. 

    max_noise_rate : float
      Smaller ---> easier learning problem (less noise)

    frac_zero_noise_rates : float
      Make problem more tractable by making a fraction of noise rates zero.
      Larger --> Easier learning problem

    prob_y : np.array of floats
      P(y=k). Sums to 1.'''
    
    # Init noise matrix to be random values from (0, max_noise_rate)
    # P(s=k|y=k')
    noise_matrix = np.random.rand(K,K) * max_noise_rate

    # Round all noise rates 
    noise_matrix = noise_matrix.round(2)

    # Initialize all P(s=k|y=k) = 0
    for i in range(K):
        noise_matrix[i][i] = 0.0

    # Compute sum for each column
    col_sum = noise_matrix.sum(axis=0)

    # For each column, randomly set noise rates to zero until P(s!=k|s=k) < 1.
    for y in range(K): # col
        col = noise_matrix.T[y]
        col_sum = np.sum(col)
        while col_sum >= 1:
            non_zero_indices = np.arange(K)[col!=0]
            s = np.random.choice(non_zero_indices)
            noise_matrix[s][y] = 0.0
            col = noise_matrix.T[y]
            col_sum = np.sum(col)

    # Set frac_zero_noise_rates of the noise rates to 0 for increased tractability.
    for s in range(K):
        for y in range(K):
            if np.random.rand() < frac_zero_noise_rates:
                noise_matrix[s][y] = 0

    # Compute sum for each column
    col_sum = noise_matrix.sum(axis=0)

    # Normalize each column such that P(s=k|y=k) = 1 - P(s!=k|s=k)
    for i in range(K):
        noise_matrix[i][i] = 1 - col_sum[i]
  
    if verbose:
        print("Average trace of noise matrix is", np.trace(noise_matrix) / float(K))
    
    return noise_matrix

