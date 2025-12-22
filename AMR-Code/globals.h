/**************************************************************************
*
*	FILENAME				:	globals.h
*
*	DESCRIPTION			:	Global Values for speech channel coding and decoding
*
**************************************************************************/


#ifndef MAX_SpFrms_per_TDMFrm
  #define MAX_SpFrms_per_TDMFrm 3
#endif


extern	int	CoderType;	/* 0 = default TETRA       */
				    /* 1 = AMR 4750 bit/s MODE */

extern	int	SpFrms_per_TDMFrm;

extern	int	N0;
extern	int	N1;
extern	int	N2;
extern	int	N0_2;
extern	int	N1_2;
extern	int	N2_2;
extern	int	N1_2_coded;
extern	int	N2_2_coded;


extern	int	Length_vocoder_frame;
extern	int	Length_2_frames;

extern	int	SIZE_TAB_CRC1;
extern	int	SIZE_TAB_CRC2;
extern	int	SIZE_TAB_CRC3;
extern	int	SIZE_TAB_CRC4;
extern	int	SIZE_TAB_CRC5;
extern	int	SIZE_TAB_CRC6;
extern	int	SIZE_TAB_CRC7;
extern	int	SIZE_TAB_CRC8;




extern	int     Fs_SpFrms_per_TDMFrm;

extern	int     Fs_N0[MAX_SpFrms_per_TDMFrm];
extern	int     Fs_N1[MAX_SpFrms_per_TDMFrm];
extern	int     Fs_N2[MAX_SpFrms_per_TDMFrm];

extern	int     Fs_N0_Tot;
extern	int     Fs_N1_Tot;
extern	int     Fs_N2_Tot;
extern	int     Fs_N1_Tot_coded;
extern	int     Fs_N2_Tot_coded;

extern	int     Fs_SIZE_TAB_CRC1;
extern	int	Fs_SIZE_TAB_CRC2;
extern	int	Fs_SIZE_TAB_CRC3;
extern	int     Fs_SIZE_TAB_CRC4;

extern	int     Fs_Fixed_Bits[MAX_SpFrms_per_TDMFrm];

