# Copyright 2009 by Peter Cock.  All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

"""SeqFeature related tests for SeqRecord objects from Bio.SeqIO.

Initially this takes matched tests of GenBank and FASTA files from the NCBI
and confirms they are consistent using our different parsers.
"""
import os
import unittest
from Bio import SeqIO
from Bio.Seq import Seq, UnknownSeq, MutableSeq
from Bio.SeqRecord import SeqRecord
from StringIO import StringIO

#Top level function as this makes it easier to use for debugging:
def write_read(filename, in_format="gb", out_format="gb") :
    gb_records = list(SeqIO.parse(open(filename),in_format))
    #Write it out...
    handle = StringIO()
    SeqIO.write(gb_records, handle, out_format)
    handle.seek(0)
    #Now load it back and check it agrees,
    gb_records2 = list(SeqIO.parse(handle,out_format))
    compare_records(gb_records, gb_records2)

def compare_record(old, new, ignore_name=False) :
    #Note the name matching is a bit fuzzy
    if not ignore_name \
    and old.id != new.id and old.name != new.name \
    and (old.id not in new.id) and (new.id not in old.id) \
    and (old.id.replace(" ","_") != new.id.replace(" ","_")) :
        raise ValueError("'%s' or '%s' vs '%s' or '%s' records" \
                         % (old.id, old.name, new.id, new.name))
    if len(old.seq) != len(new.seq) :
        raise ValueError("%i vs %i" % (len(old.seq), len(new.seq)))
    if str(old.seq).upper() != str(new.seq).upper() :
        if len(old.seq) < 200 :
            raise ValueError("'%s' vs '%s'" % (old.seq, new.seq))
        else :
            raise ValueError("'%s...' vs '%s...'" % (old.seq[:100], new.seq[:100]))
    if old.features and new.features :
        return compare_features(old.features, new.features)
    #Just insist on at least one word in common:
    if (old.description or new.description) \
    and not set(old.description.split()).intersection(new.description.split()):
        raise ValueError("%s versus %s" \
                         % (repr(old.description), repr(new.description)))
    #TODO - check annotation
    return True

def compare_records(old_list, new_list, ignore_name=False) :
    """Check two lists of SeqRecords agree, raises a ValueError if mismatch."""
    if len(old_list) != len(new_list) :
        raise ValueError("%i vs %i records" % (len(old_list), len(new_list)))
    for old, new in zip(old_list, new_list) :
        if not compare_record(old,new,ignore_name) :
            return False
    return True

def compare_feature(old, new, ignore_sub_features=False) :
    """Check two SeqFeatures agree."""
    if old.type != new.type :
        raise ValueError("Type %s versus %s" % (old.type, new.type))
    if old.location.nofuzzy_start != new.location.nofuzzy_start \
    or old.location.nofuzzy_end != new.location.nofuzzy_end :
        raise ValueError("%s versus %s:\n%s\nvs:\n%s" \
                         % (old.location, new.location, str(old), str(new)))
    if old.strand != new.strand :
        raise ValueError("Different strand:\n%s\nvs:\n%s" % (str(old), str(new)))
    if old.location.start != new.location.start :
        raise ValueError("Start %s versus %s:\n%s\nvs:\n%s" \
                         % (old.location.start, new.location.start, str(old), str(new)))
    if old.location.end != new.location.end :
        raise ValueError("End %s versus %s:\n%s\nvs:\n%s" \
                         % (old.location.end, new.location.end, str(old), str(new)))
    if not ignore_sub_features :
        if len(old.sub_features) != len(new.sub_features) :
            raise ValueError("Different sub features")
        for a,b in zip(old.sub_features, new.sub_features) :
            if not compare_feature(a,b) :
                return False
    #This only checks key shared qualifiers
    #Would a white list be easier?
    #for key in ["name","gene","translation","codon_table","codon_start","locus_tag"] :
    for key in set(old.qualifiers.keys()).intersection(new.qualifiers.keys()):
        if key in ["db_xref","protein_id","product","note"] :
            #EMBL and GenBank files are use different references/notes/etc
            continue
        if old.qualifiers[key] != new.qualifiers[key] :
            raise ValueError("Qualifier mis-match for %s:\n%s\n%s" \
                             % (key, old.qualifiers[key], new.qualifiers[key]))
    return True

def compare_features(old_list, new_list, ignore_sub_features=False) :
    """Check two lists of SeqFeatures agree, raises a ValueError if mismatch."""
    if len(old_list) != len(new_list) :
        raise ValueError("%i vs %i features" % (len(old_list), len(new_list)))
    for old, new in zip(old_list, new_list) :
        #This assumes they are in the same order
        if not compare_feature(old,new,ignore_sub_features) :
            return False
    return True

class NC_005816(unittest.TestCase):
    basename = "NC_005816"
    emblname = "AE017046"
    table = 11
    skip_trans_test = []
    __doc__ = "Tests using %s GenBank and FASTA files from the NCBI" % basename
    
    def test_CDS(self) :
        #"""Checking GenBank CDS translations vs FASTA faa file."""
        filename = os.path.join("GenBank",self.basename+".gb")
        gb_cds = list(SeqIO.parse(open(filename),"genbank-cds"))
        filename = os.path.join("GenBank",self.basename+".faa")
        fasta = list(SeqIO.parse(open(filename),"fasta"))
        compare_records(gb_cds, fasta)

    def test_Translations(self):
        #"""Checking translation of FASTA features (faa vs ffn)."""
        filename = os.path.join("GenBank",self.basename+".faa")
        faa_records = list(SeqIO.parse(open(filename),"fasta"))
        filename = os.path.join("GenBank",self.basename+".ffn")
        ffn_records = list(SeqIO.parse(open(filename),"fasta"))
        self.assertEqual(len(faa_records),len(ffn_records))
        for faa, fna in zip(faa_records, ffn_records) :
            translation = fna.seq.translate(self.table)
            if translation[0] != "M" and faa.seq[0] == "M" :
                #Hack until we fix Bug 2783
                translation = Seq("M", translation.alphabet) + translation[1:]
            if faa.id in self.skip_trans_test :
                continue
            if (str(translation) != str(faa.seq)) \
            and (str(translation) != str(faa.seq)+"*") :
                t = SeqRecord(translation, id="Translation",
                              description="Table %s" % self.table)
                raise ValueError("FAA vs FNA translation problem:\n%s\n%s\n%s\n" \
                                 % (fna.format("fasta"),
                                    t.format("fasta"),
                                    faa.format("fasta")))

    def test_Genome(self) :
        #"""Checking GenBank sequence vs FASTA fna file."""
        filename = os.path.join("GenBank",self.basename+".gb")
        gb_record = SeqIO.read(open(filename),"genbank")
        filename = os.path.join("GenBank",self.basename+".fna")
        fa_record = SeqIO.read(open(filename),"fasta")
        compare_record(gb_record, fa_record)
        if self.emblname is None :
            return
        filename = os.path.join("EMBL",self.emblname+".embl")
        embl_record = SeqIO.read(open(filename),"embl")
        compare_record(gb_record, embl_record, ignore_name=True)

    def test_Features(self) :
        #"""Checking GenBank features sequences vs FASTA ffn file."""
        filename = os.path.join("GenBank",self.basename+".gb")
        gb_record = SeqIO.read(open(filename),"genbank")
        features = [f for f in gb_record.features if f.type=="CDS"]
        filename = os.path.join("GenBank",self.basename+".ffn")
        fa_records = list(SeqIO.parse(open(filename),"fasta"))
        self.assertEqual(len(fa_records), len(features))
        #This assumes they are in the same order...
        for fa_record, f in zip(fa_records, features) :
            #TODO - check the FASTA ID line against the co-ordinates?
            if f.sub_features :
                #TODO - Add this functionality to Biopython itself...
                self.assertEqual(f.location_operator,"join")
                f_subs = [gb_record.seq[f_sub.location.nofuzzy_start:f_sub.location.nofuzzy_end] \
                          for f_sub in f.sub_features]
                f_seq = Seq("".join(map(str,f_subs)),f_subs[0].alphabet)
            else :
                f_seq = gb_record.seq[f.location.nofuzzy_start:f.location.nofuzzy_end]
            if f.strand == -1 : f_seq = f_seq.reverse_complement()
            self.assertEqual(len(fa_record.seq),
                             len(f_seq))
            self.assertEqual(str(fa_record.seq),
                             str(f_seq))


class NC_006980(NC_005816):
    #This includes several joins and fuzzy joins :)
    basename = "NC_006980"
    emblname = None
    table = 1
    skip_trans_test = ["gi|126643907|ref|XP_001388140.1|"]
    __doc__ = "Tests using %s GenBank and FASTA files from the NCBI" % basename
    #TODO - neat way to change the docstrings...

class TestWriteRead(unittest.TestCase) :
    """Test can write and read back files."""

    #Slow:
    #def test_NC_006980(self) :
    #    """Write and read back NC_006980.gb"""
    #    write_read(os.path.join("GenBank", "NC_006980.gb"), "gb", "gb")

    def test_NC_005816(self) :
        """Write and read back NC_005816.gb"""
        write_read(os.path.join("GenBank", "NC_005816.gb"), "gb", "gb")

    def test_gbvrl1_start(self) :
        """Write and read back gbvrl1_start.seq"""
        write_read(os.path.join("GenBank", "gbvrl1_start.seq"), "gb", "gb")

    def test_NT_019265(self) :
        """Write and read back NT_019265.gb"""
        write_read(os.path.join("GenBank", "NT_019265.gb"), "gb", "gb")

    def test_cor6(self) :
        """Write and read back cor6_6.gb"""
        write_read(os.path.join("GenBank", "cor6_6.gb"), "gb", "gb")

    def test_arab1(self) :
        """Write and read back arab1.gb"""
        write_read(os.path.join("GenBank", "arab1.gb"), "gb", "gb")

    def test_one_of(self) :
        """Write and read back of_one.gb"""
        write_read(os.path.join("GenBank", "one_of.gb"), "gb", "gb")

    def test_pri1(self) :
        """Write and read back pri1.gb"""
        write_read(os.path.join("GenBank", "pri1.gb"), "gb", "gb")

    def test_noref(self) :
        """Write and read back noref.gb"""
        write_read(os.path.join("GenBank", "noref.gb"), "gb", "gb")

    def test_origin_line(self) :
        """Write and read back origin_line.gb"""
        write_read(os.path.join("GenBank", "origin_line.gb"), "gb", "gb")

    def test_dbsource_wrap(self) :
        """Write and read back dbsource_wrap.gb"""
        write_read(os.path.join("GenBank", "dbsource_wrap.gb"), "gb", "gb")

    def test_blank_seq(self) :
        """Write and read back blank_seq.gb"""
        write_read(os.path.join("GenBank", "blank_seq.gb"), "gb", "gb")

    def test_extra_keywords(self) :
        """Write and read back extra_keywords.gb"""
        write_read(os.path.join("GenBank", "extra_keywords.gb"), "gb", "gb")

    def test_protein_refseq(self) :
        """Write and read back protein_refseq.gb"""
        write_read(os.path.join("GenBank", "protein_refseq.gb"), "gb", "gb")

    def test_protein_refseq2(self) :
        """Write and read back protein_refseq2.gb"""
        write_read(os.path.join("GenBank", "protein_refseq2.gb"), "gb", "gb")

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity = 2)
    unittest.main(testRunner=runner)
