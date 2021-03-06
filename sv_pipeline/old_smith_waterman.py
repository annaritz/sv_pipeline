"""
Taken from https://gist.github.com/radaniba/11019717
Radhouane Aniba
(c) 2013 Ryan Boehning

A Python implementation of the Smith-Waterman algorithm for local alignment
of nucleotide sequences.

Details:
    - local alignment
    - overlap (ignores starting and ending subsequences when necessary)
    - constant gap penalty
    - gap penalty = -1
    - mismatch = -1
    - match = 2

These scores are taken from Wikipedia.
en.wikipedia.org/wiki/Smith%E2%80%93Waterman_algorithm
"""

from __future__ import print_function
import sys
import time
import unittest
from Bio import SeqIO, pairwise2

class Timer:
    """A helper class for timing

    http://stackoverflow.com/questions/5849800/tic-toc-functions-analog-in-python
    """
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()
        if self.name:
            print('==> [Entering: %s]' % self.name)

    def __exit__(self, type, value, traceback):
        if self.name:
            print('<== [Exiting : %s] ' % self.name, end='')
        print('Elapsed: %s' % (time.time() - self.tstart))


def align(seq1, seq2):
    """Aligns two sequences seq1 and seq2 with
    Smith-Waterman, local, overlap alignment.

    Args:
        seq1 (string): first nucleotide sequence
        seq2 (string): second nucleotide sequence

    Returns:
        seq1_aligned (string): the aligned first nucleotide sequence
        seq2_aligned (string): the aligned second nucleotide sequence
        score (int): the max value in the score matrix

    Examples:
        >>> align("TAG", "GAG")
        ('AG', 'AG', 4)

    """
    # The scoring matrix contains an extra row and column for the gap (-), hence
    # the +1 here.
    rows = len(seq1) + 1
    cols = len(seq2) + 1

    # Initialize the scoring matrix.
    score_matrix, start_pos = _create_score_matrix(rows, cols, seq1, seq2)
    x, y = start_pos
    score = score_matrix[x][y]

    # Traceback. Find the optimal path through the scoring matrix. This path
    # corresponds to the optimal local sequence alignment.
    seq1_aligned, seq2_aligned = _traceback(score_matrix, start_pos, seq1, seq2)

    assert len(seq1_aligned) == len(seq2_aligned), 'aligned strings are not the same size'

    return seq1_aligned, seq2_aligned, score

def _create_score_matrix(rows, cols, seq1, seq2):
    """Create a matrix of scores representing trial alignments of the two sequences.

    Sequence alignment can be treated as a graph search problem. This function
    creates a graph (2D matrix) of scores, which are based on trial alignments
    of different base pairs. The path with the highest cummulative score is the
    best alignment.
    """

    def calc_score(matrix, x, y):
        """Calculate score for a given x, y position in the scoring matrix.
        The score is based on the up, left, and upper-left neighbors.
        """

        match = 2
        mismatch = -1
        gap = -1

        similarity = match if seq1[x - 1] == seq2[y - 1] else mismatch

        diag_score = matrix[x - 1][y - 1] + similarity
        up_score = matrix[x - 1][y] + gap
        left_score = matrix[x][y - 1] + gap

        return max(0, diag_score, up_score, left_score)

    score_matrix = [[0 for _ in range(cols)] for _ in range(rows)]

    # Fill the scoring matrix.
    # Keep left column and top row as 0s for overlap alignment.
    max_score = 0
    max_pos = None # The row and columbn of the highest score in matrix.
    for i in range(1, rows):
        for j in range(1, cols):
            score = calc_score(score_matrix, i, j)
            if score > max_score:
                max_score = score
                max_pos = (i, j)

            score_matrix[i][j] = score

    assert max_pos is not None, 'the x, y position with the highest score was not found'
    return score_matrix, max_pos

def _traceback(score_matrix, start_pos, seq1, seq2):
    """Find the optimal path through the matrix.

    This function traces a path from the bottom-right to the top-left corner of
    the scoring matrix. Each move corresponds to a match, mismatch, or gap in one
    or both of the sequences being aligned. Moves are determined by the score of
    three adjacent squares: the upper square, the left square, and the diagonal
    upper-left square.

    WHAT EACH MOVE REPRESENTS
        diagonal: match/mismatch
        up:       gap in sequence 1
        left:     gap in sequence 2
    """

    END, DIAG, UP, LEFT = range(4)
    def _next_move(score_matrix, x, y):
        diag = score_matrix[x - 1][y - 1]
        up = score_matrix[x - 1][y]
        left = score_matrix[x][y - 1]

        if diag >= up and diag >= left:          # Tie goes to the DIAG move.
            return DIAG if diag != 0 else END    # 1 signals a DIAG move. 0 signals the end.

        elif up > diag and up >= left:           # Tie goes to UP move.
            return UP if up != 0 else END        # UP move or end.

        elif left > diag and left > up:
            return LEFT if left != 0 else END    # LEFT move or end.
        else:
            # Execution should not reach here.
            raise ValueError('invalid move during traceback')

    aligned_seq1 = []
    aligned_seq2 = []
    x, y = start_pos
    move = _next_move(score_matrix, x, y)
    while move != END:
        if move == DIAG:
            aligned_seq1.append(seq1[x - 1])
            aligned_seq2.append(seq2[y - 1])
            x -= 1
            y -= 1
        elif move == UP:
            aligned_seq1.append(seq1[x - 1])
            aligned_seq2.append('-')
            x -= 1
        elif move == LEFT:
            aligned_seq1.append('-')
            aligned_seq2.append(seq2[y - 1])
            y -= 1
        else:
            raise ValueError("Invalid move value")
        move = _next_move(score_matrix, x, y)

    aligned_seq1.append(seq1[x - 1])
    aligned_seq2.append(seq2[y - 1])

    ret = ''.join(reversed(aligned_seq1)), ''.join(reversed(aligned_seq2))
    return ret


def _print_alignment(seq1_aligned, seq2_aligned):
    alignment_str, idents, gaps, mismatches = _alignment_string(seq1_aligned, seq2_aligned)
    alength = len(seq1_aligned)

    print(' Identities = {0}/{1} ({2:.1%}), Gaps = {3}/{4} ({5:.1%}), mismatches = {6}'
          .format(idents,
                  alength,
                  idents / alength,
                  gaps,
                  alength,
                  gaps / alength,
                  mismatches
                 )
         )

    for i in range(0, alength, 60):
        seq1_slice = seq1_aligned[i:i+60]
        print('Query  {0:<4}  {1}  {2:<4}'.format(i + 1, seq1_slice, i + len(seq1_slice)))
        print('             {0}'.format(alignment_str[i:i+60]))
        seq2_slice = seq2_aligned[i:i+60]
        print('Sbjct  {0:<4}  {1}  {2:<4}'.format(i + 1, seq2_slice, i + len(seq2_slice)))
        print()


def _alignment_string(aligned_seq1, aligned_seq2):
    """Construct a special string showing identities, gaps, and mismatches.

    This string is printed between the two aligned sequences and shows the
    identities (|), gaps (-), and mismatches (:). As the string is constructed,
    it also counts number of identities, gaps, and mismatches and returns the
    counts along with the alignment string.

    AAGGATGCCTCAAATCGATCT-TTTTCTTGG-
    ::||::::::||:|::::::: |:  :||:|   <-- alignment string
    CTGGTACTTGCAGAGAAGGGGGTA--ATTTGG
    """

    # Build the string as a list of characters to avoid costly string
    # concatenation.
    idents, gaps, mismatches = 0, 0, 0
    alignment_string = []
    for base1, base2 in zip(aligned_seq1, aligned_seq2):
        if base1 == base2:
            alignment_string.append('|')
            idents += 1
        elif '-' in (base1, base2):
            alignment_string.append(' ')
            gaps += 1
        else:
            alignment_string.append(':')
            mismatches += 1
    return ''.join(alignment_string), idents, gaps, mismatches

def _fasta_dict(filename):
    """Generates a dictionary mapping read name to sequence

    SeqIO.parse returns an iterator to records,
    where each record is a Bio.SeqIO.SeqRecord

    # improve this -- can't grab all reads
    """

    with open(filename, 'r') as fasta_file:
        ret_dict = {record.id: str(record.seq) \
                for record in SeqIO.parse(fasta_file, "fasta")}
    return ret_dict

def get_alignment_scores(read_pairs, fasta_file):
    """Returns a dictionary mapping a read_pair to its alignment score

    fasta_file is path to fasta filename containing sequences
    for the read_pairs

    read_pairs should be a list of 2-tuples.
    e.g. read_pairs = [(read0, read1), (read2, read3), ...]
    """

    fasta_dict = _fasta_dict(fasta_file)
    score_dict = {}

    for read0, read1 in read_pairs:
        seq0 = fasta_dict[read0]
        seq1 = fasta_dict[read1]
        _, _, score = align(seq0, seq1)
        score_dict[(read0, read1)] = score
    return score_dict




class ScoreMatrixTest(unittest.TestCase):
    """Compare the matrix produced by create_score_matrix() with a known matrix.
    """
    def test_matrix(self):
        """Tests that a score matrix is correct for a fairly simple case.
        """
        # From Wikipedia (en.wikipedia.org/wiki/Smith%E2%80%93Waterman_algorithm)
        #                -   A   C   A   C   A   C   T   A
        known_matrix = [[0, 0, 0, 0, 0, 0, 0, 0, 0],     # -
                        [0, 2, 1, 2, 1, 2, 1, 0, 2],     # A
                        [0, 1, 1, 1, 1, 1, 1, 0, 1],     # G
                        [0, 0, 3, 2, 3, 2, 3, 2, 1],     # C
                        [0, 2, 2, 5, 4, 5, 4, 3, 4],     # A
                        [0, 1, 4, 4, 7, 6, 7, 6, 5],     # C
                        [0, 2, 3, 6, 6, 9, 8, 7, 8],     # A
                        [0, 1, 4, 5, 8, 8, 11, 10, 9],  # C
                        [0, 2, 3, 6, 7, 10, 10, 10, 12]]  # A


        seq1 = 'AGCACACA'
        seq2 = 'ACACACTA'
        rows = len(seq1) + 1
        cols = len(seq2) + 1

        matrix_to_test, _ = _create_score_matrix(rows, cols, seq1, seq2)
        self.assertEqual(known_matrix, matrix_to_test)

    def test_fasta(self):
        pass
        #overlaps = [('m150213_074729_42177R_c100777662550000001823160908051505_s1_p0/70715/9957_22166',
        #'m150126_093705_42156_c100779662550000001823165208251525_s1_p0/144605/28461_40297')]

        #fasta_filename = 'example.fa'
        #scores = get_alignment_scores(overlaps, fasta_filename)
        #print(scores)



    def test_weird_case(self):
        """A weird case where overlap alignment doesn't seem to work.
        Debugged, but couldn't figure out the proper fix.
        """
        seq1 = "AAT"
        seq2 = "AT"

        aligned1, aligned2, score = align(seq1, seq2)
        #_print_alignment(aligned1, aligned2)
        #print("score: {}".format(score))

def test_normal_case():
    """A simple example on how to use the module.
    """
    seq1 = "ATAGACGACATACAGACAGCATACAGACAGCATACAGA"
    seq2 = "TTTAGCATGCGCATATCAGCAATACAGACAGATACG"

    aligned1, aligned2, score = align(seq1, seq2)
    _print_alignment(aligned1, aligned2)
    print("score: {}".format(score))

#test_normal_case()

#if __name__ == '__main__':
#    unittest.main()



#
#def their_align(x, y):
#    return pairwise2.align.localxx(x, y)
#
#
#
#def timing():
d = _fasta_dict('example.fa')
r0 = 'm150213_074729_42177R_c100777662550000001823160908051505_s1_p0/70715/9957_22166'
r1 = 'm150126_093705_42156_c100779662550000001823165208251525_s1_p0/144605/28461_40297'
seq0 = d[r0]
seq1 = d[r1]
print(seq0[:1000])
print(seq1[:1000])
#
#    for i in [100, 500, 1000]:
#        s0 = seq0[:i]
#        s1 = seq1[:i]
#        with Timer("align {}".format(i)):
#            align(s0, s1)
#
#timing()
#
#"""
#==> [Entering: their_align 100]
#<== [Exiting : their_align 100] Elapsed: 0.058339834213256836
#==> [Entering: their_align 500]
#<== [Exiting : their_align 500] Elapsed: 1.428382158279419
#==> [Entering: their_align 1000]
#<== [Exiting : their_align 1000] Elapsed: 8.796906471252441
#
#==> [Entering: align 100]
#<== [Exiting : align 100] Elapsed: 0.012089252471923828
#==> [Entering: align 500]
#<== [Exiting : align 500] Elapsed: 0.3024263381958008
#==> [Entering: align 1000]
#<== [Exiting : align 1000] Elapsed: 1.2689251899719238
#"""
#
#
#
